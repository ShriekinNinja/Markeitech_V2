from __future__ import annotations

import asyncio
import json
import socket
from dataclasses import asdict
from pathlib import Path
from queue import Empty, Full, Queue
from threading import Event, Thread
from time import monotonic, time
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from markeitech.acquisition.dashboard_history import DashboardHistoryRequest
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
    actors, the cache, provider clients or configuration secrets. A bounded request
    mailbox carries validated history intents back to DashboardActor.
    Slow clients receive a new snapshot after reconnect; raw tick delivery is not promised.
    """

    def __init__(self, config: DashboardConfig, initial: dict) -> None:
        self.config = config
        self._mailbox: Queue[dict] = Queue(maxsize=1)
        self._latest = initial
        self._epoch = str(uuid4())
        self._clients = 0
        self._history_requests: Queue[tuple[float, DashboardHistoryRequest]] = Queue(
            config.maximum_history_requests
        )
        self._history_results: Queue[dict] = Queue(config.maximum_history_requests)
        self._history_jobs: dict[str, tuple[float, dict]] = {}
        self._history_admissions = 0
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
            "history_page_minutes": self.config.history_page_minutes,
            "history_timeout_seconds": self.config.history_request_timeout_seconds,
        }

    def take_history_requests(self) -> tuple[DashboardHistoryRequest, ...]:
        """Drain bounded operator intents on the actor thread without blocking."""
        requests = []
        for _ in range(self.config.maximum_history_requests):
            try:
                deadline, command = self._history_requests.get_nowait()
                if monotonic() < deadline:
                    requests.append(command)
            except Empty:
                break
        return tuple(requests)

    def finish_history(self, result: dict) -> None:
        """Offer a detached terminal result; an unconsumed result expires in the web worker."""
        try:
            self._history_results.put_nowait(result)
        except Full:
            # Never block the market-data thread. The HTTP job has a finite deadline.
            return

    def _read_history(self) -> None:
        now = monotonic()
        self._history_jobs = {
            key: value
            for key, value in self._history_jobs.items()
            if now - value[0] < self.config.history_request_timeout_seconds
        }
        for _ in range(self.config.maximum_history_requests):
            try:
                result = self._history_results.get_nowait()
            except Empty:
                break
            if result["request_id"] in self._history_jobs:
                started, original = self._history_jobs[result["request_id"]]
                self._history_jobs[result["request_id"]] = (started, {**original, **result})

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

        @app.post("/api/history", status_code=202)
        async def history(request: Request) -> dict:
            if request.headers.get("content-type", "").split(";")[0] != "application/json":
                raise HTTPException(415, "JSON history request required")
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > 1024:
                    raise HTTPException(413, "History request is too large")
            try:
                payload = json.loads(body)
                if not isinstance(payload, dict) or payload.keys() != {
                    "instrument_id",
                    "start",
                    "end",
                }:
                    raise ValueError("invalid fields")
                command = DashboardHistoryRequest(str(uuid4()), **payload)
            except (ValueError, TypeError):
                raise HTTPException(
                    422, "Use an instrument and UTC minute start/end bounds"
                ) from None
            view = self._view(command.instrument_id)
            row = next(
                r for r in view["instruments"] if r["instrument_id"] == command.instrument_id
            )
            if "watchlist_last" not in row["capabilities"]:
                raise HTTPException(422, "Instrument has no configured bar feed")
            if command.end > int(time()) // 60 * 60:
                raise HTTPException(422, "History must end at a completed UTC minute")
            if command.end - command.start > self.config.history_page_minutes * 60:
                raise HTTPException(422, "History page exceeds the configured duration")
            self._read_history()
            for _, job in self._history_jobs.values():
                if all(job.get(key) == value for key, value in payload.items()):
                    if job["status"] != "PENDING":
                        job["delivered"] = True
                    return job
            # Completed pages need not occupy admission slots once returned.
            for key in tuple(self._history_jobs):
                if self._history_jobs[key][1].get("delivered"):
                    del self._history_jobs[key]
            if len(self._history_jobs) >= self.config.maximum_history_requests:
                raise HTTPException(429, "History request limit reached")
            if self._history_admissions >= self.config.maximum_history_requests_per_session:
                raise HTTPException(
                    429, "History session budget reached; restart the system to reset"
                )
            try:
                self._history_requests.put_nowait(
                    (monotonic() + self.config.history_request_timeout_seconds, command)
                )
            except Full:
                raise HTTPException(429, "History request queue is full") from None
            result = {**asdict(command), "status": "PENDING"}
            self._history_jobs[command.request_id] = (monotonic(), result)
            self._history_admissions += 1
            return result

        @app.get("/api/history/{request_id}")
        async def history_result(request_id: str) -> dict:
            self._read_history()
            job = self._history_jobs.get(request_id)
            if job is None:
                raise HTTPException(404, "History request expired or is unknown")
            if job[1]["status"] != "PENDING":
                job[1]["delivered"] = True
            return job[1]

        @app.get("/api/events")
        async def events(request: Request, instrument_id: str | None = None) -> StreamingResponse:
            self._view(instrument_id)
            if self._clients >= self.config.maximum_clients:
                raise HTTPException(503, "Dashboard connection limit reached")
            self._clients += 1

            async def stream():  # noqa: ANN202
                sequence = -1
                previous_selected = None
                previous_candles = {}
                try:
                    while not self.stopping.is_set() and not await request.is_disconnected():
                        view = self._view(instrument_id)
                        if view["sequence"] != sequence:
                            reset = sequence == -1 or view["selected"] != previous_selected
                            candles = view["candles"]
                            view["reset"] = reset
                            view["window_start"] = candles[0]["time"] if candles else None
                            if not reset:
                                view["candles"] = [
                                    bar
                                    for bar in candles
                                    if previous_candles.get(bar["time"]) != bar
                                ]
                            previous_candles = {bar["time"]: bar for bar in candles}
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
