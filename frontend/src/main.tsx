import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "./styles.css";

function App() {
  return (
    <main className="shell">
      <section className="topbar">
        <div>
          <h1>Markeitech</h1>
          <p>NQ data cockpit bootstrap</p>
        </div>
        <span className="status">Stage 0</span>
      </section>
      <section className="workspace">
        <div className="panel chart-panel">
          <h2>Primary Chart</h2>
          <div className="chart-placeholder" />
        </div>
        <aside className="panel side-panel">
          <h2>Runtime</h2>
          <dl>
            <div>
              <dt>Mode</dt>
              <dd>Data only</dd>
            </div>
            <div>
              <dt>Execution</dt>
              <dd>Disabled</dd>
            </div>
            <div>
              <dt>Instrument</dt>
              <dd>Explicit NQ contract required</dd>
            </div>
          </dl>
        </aside>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
