from __future__ import annotations

import asyncio
import json
import socket
from pathlib import Path
from queue import Empty, Full, Queue
from threading import Event, Thread
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from markeitech.dashboard.config import DashboardConfig

_STATIC = Path(__file__).parent / "static"


class _ReadyServer(uvicorn.Server):
    def __init__(self, config: uvicorn.Config, ready: Event) -> None:
        super().__init__(config)
        self._ready = ready

    async def startup(self, sockets: list[socket.socket] | None = None) -> None:
        await super().startup(sockets=sockets)
        if self.started:
            self._ready.set()


class DashboardServer:
    """Serve loopback HTTP/SSE in one actor-owned thread with a one-snapshot mailbox.

    The web thread receives detached projections only. It cannot reach native
    actors, the cache, provider clients, configuration secrets, or acquisition.
    Slow clients receive a new snapshot after reconnect; raw tick delivery is not promised.
    """

    def __init__(self, config: DashboardConfig, initial: dict) -> None:
        self.config = config
        self._mailbox: Queue[dict] = Queue(maxsize=1)
        self._latest = initial
        self._epoch = str(uuid4())
        self._clients = 0
        self._thread: Thread | None = None
        self._server: uvicorn.Server | None = None
        self.stopping = Event()
        self.ready = Event()
        self.failure: str | None = None
        self.app = self._application()

    @property
    def epoch(self) -> str:
        """Return the identity shared by readiness notification and browser snapshots."""
        return self._epoch

    def publish(self, snapshot: dict) -> None:
        """Offer the newest detached snapshot without waiting for a browser or lock."""
        if self.stopping.is_set():
            return
        try:
            self._mailbox.put_nowait(snapshot)
        except Full:
            try:
                self._mailbox.get_nowait()
            except Empty:
                pass
            self._mailbox.put_nowait(snapshot)

    def _read(self) -> dict:
        try:
            self._latest = self._mailbox.get_nowait()
        except Empty:
            pass
        return self._latest

    def _view(self, instrument_id: str | None) -> dict:
        snapshot = self._read()
        ids = [row["instrument_id"] for row in snapshot["instruments"]]
        selected = instrument_id or (ids[0] if ids else None)
        if selected is not None and selected not in ids:
            raise HTTPException(404, "Instrument is not in the dashboard watchlist")
        return {
            **{key: value for key, value in snapshot.items() if key != "candles"},
            "epoch": self._epoch,
            "selected": selected,
            "candles": snapshot["candles"].get(selected, []),
        }

    def _application(self) -> FastAPI:
        app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

        @app.middleware("http")
        async def local_only(request: Request, call_next):  # noqa: ANN001, ANN202
            hosts = {f"127.0.0.1:{self.config.port}", f"localhost:{self.config.port}"}
            host = request.headers.get("host", "")
            origin = request.headers.get("origin")
            if host not in hosts or (origin is not None and origin != f"http://{host}"):
                return JSONResponse({"detail": "Local same-origin access only"}, status_code=403)
            if self.stopping.is_set():
                return JSONResponse({"detail": "System is stopping"}, status_code=503)
            response = await call_next(request)
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                "connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; "
                "base-uri 'none'; form-action 'none'"
            )
            return response

        @app.get("/")
        async def index() -> FileResponse:
            return FileResponse(_STATIC / "index.html")

        @app.get("/api/snapshot")
        async def snapshot(instrument_id: str | None = None) -> dict:
            return self._view(instrument_id)

        @app.get("/api/events")
        async def events(request: Request, instrument_id: str | None = None) -> StreamingResponse:
            self._view(instrument_id)
            if self._clients >= self.config.maximum_clients:
                raise HTTPException(503, "Dashboard connection limit reached")
            self._clients += 1

            async def stream():  # noqa: ANN202
                sequence = -1
                previous_selected = None
                last_time = None
                try:
                    while not self.stopping.is_set() and not await request.is_disconnected():
                        view = self._view(instrument_id)
                        if view["sequence"] != sequence:
                            reset = sequence == -1 or view["selected"] != previous_selected
                            candles = view["candles"]
                            view["reset"] = reset
                            view["window_start"] = candles[0]["time"] if candles else None
                            if not reset and last_time is not None:
                                view["candles"] = [
                                    bar for bar in candles if bar["time"] > last_time
                                ]
                            if candles:
                                last_time = candles[-1]["time"]
                            sequence, previous_selected = view["sequence"], view["selected"]
                            payload = json.dumps(view, separators=(",", ":"))
                            yield f"event: update\ndata: {payload}\n\n"
                        else:
                            yield ": heartbeat\n\n"
                        await asyncio.sleep(self.config.publish_interval_ms / 1000)
                    yield "event: stopping\ndata: {}\n\n"
                finally:
                    self._clients -= 1

            return StreamingResponse(stream(), media_type="text/event-stream")

        app.mount("/static", StaticFiles(directory=_STATIC), name="static")
        return app

    def start(self) -> None:
        """Start the server worker; no socket or filesystem work runs in actor callbacks."""
        if self._thread is not None:
            raise RuntimeError("dashboard server already started")
        self._thread = Thread(target=self._run, name="markeitech-dashboard", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(("127.0.0.1", self.config.port))
                sock.setblocking(False)
                server = _ReadyServer(
                    uvicorn.Config(
                        self.app,
                        host="127.0.0.1",
                        port=self.config.port,
                        access_log=False,
                        log_level="warning",
                        lifespan="off",
                        timeout_graceful_shutdown=max(1, self.config.shutdown_timeout_seconds - 1),
                        ws="none",
                    ),
                    self.ready,
                )
                self._server = server
                if self.stopping.is_set():
                    return
                asyncio.run(server.serve(sockets=[sock]))
        except Exception as exc:  # noqa: BLE001
            self.failure = type(exc).__name__
        finally:
            self.ready.clear()

    def stop(self) -> bool:
        """Close SSE streams and join the web worker within its shutdown deadline."""
        self.stopping.set()
        if self._server is not None:
            self._server.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout=self.config.shutdown_timeout_seconds)
            return not self._thread.is_alive()
        return True
