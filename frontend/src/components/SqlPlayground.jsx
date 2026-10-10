import { useEffect, useRef, useState } from "react";

import { useI18n } from "../i18n";
import CodeEditor from "./CodeEditor";
import { Icon } from "./Icon";

function newWorker() {
  return new Worker(new URL("../sql/sql.worker.js", import.meta.url));
}

function Cell({ value }) {
  if (value === null) return <span className="muted">NULL</span>;
  if (value instanceof Uint8Array) return <span className="muted">BLOB</span>;
  return String(value);
}

/** A "try it yourself" SQL editor. SQLite runs in the browser (sql.js), so no server is involved. */
export default function SqlPlayground({ initialCode = "", height = 300 }) {
  const { t } = useI18n();
  const [code, setCode] = useState(initialCode);
  const [results, setResults] = useState([]);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("idle"); // idle | loading | running
  const worker = useRef(null);
  const loadedOnce = useRef(false);
  const tr = useRef(t); // the worker's handlers outlive renders, so they read the current language from here

  useEffect(() => () => worker.current?.terminate(), []);
  useEffect(() => {
    tr.current = t;
  }, [t]);

  function run() {
    if (!worker.current) {
      worker.current = newWorker();
      worker.current.onmessage = ({ data }) => {
        if (data.type === "started") {
          loadedOnce.current = true;
          setStatus("running");
        } else if (data.type === "done") {
          setResults(data.results);
          setError(data.error || "");
          setStatus("idle");
        } else if (data.type === "error") {
          setError(tr.current("sql.startFailed", { error: data.detail }));
          setStatus("idle");
        }
      };
      worker.current.onerror = (event) => {
        setError(event.message || tr.current("python.crashed"));
        worker.current?.terminate();
        worker.current = null;
        setStatus("idle");
      };
    }
    setResults([]);
    setError("");
    setStatus(loadedOnce.current ? "running" : "loading");
    worker.current.postMessage({ type: "run", code });
  }

  function stop() {
    worker.current?.terminate();
    worker.current = null;
    loadedOnce.current = false;
    setError(t("python.stopped"));
    setStatus("idle");
  }

  const busy = status !== "idle";

  return (
    <div className="playground sql-playground">
      <div className="playground-bar">
        <strong className="playground-title">
          <Icon name="database" /> SQL
        </strong>
        <button
          className="btn btn-sm btn-secondary"
          onClick={() => {
            setCode(initialCode);
            setResults([]);
            setError("");
          }}
          disabled={busy}
        >
          <Icon name="reset" /> {t("common.reset")}
        </button>
        {busy ? (
          <button className="btn btn-sm btn-danger" onClick={stop}>
            <Icon name="stop" /> {t("python.stop")}
          </button>
        ) : (
          <button className="btn btn-sm btn-success" onClick={run}>
            <Icon name="play" /> {t("common.run")}
          </button>
        )}
      </div>
      <div className="playground-panes">
        <CodeEditor value={code} onChange={setCode} language="sql" onRun={() => !busy && run()} ariaLabel={t("sql.editor")} minHeight={height} />
        <div className="sql-output" aria-live="polite" style={{ minHeight: height }}>
          {status === "loading" && <p className="muted">{t("sql.loading")}</p>}
          {status === "idle" && !error && results.length === 0 && <p className="muted">{t("sql.empty")}</p>}
          {results.map((result, i) =>
            result.columns ? (
              <div key={i} className="sql-result">
                <code className="sql-statement">{result.sql}</code>
                {result.rows.length ? (
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          {result.columns.map((column, c) => (
                            <th key={c}>{column}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {result.rows.map((row, r) => (
                          <tr key={r}>
                            {row.map((value, c) => (
                              <td key={c}>
                                <Cell value={value} />
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="small muted">{t("sql.noRows")}</p>
                )}
                {result.total > result.rows.length && (
                  <p className="small muted">{t("sql.moreRows", { shown: result.rows.length, total: result.total })}</p>
                )}
              </div>
            ) : (
              result.changed > 0 && (
                <p key={i} className="small sql-changed">
                  {t("sql.changed", { n: result.changed })} <code>{result.sql.split("\n")[0].slice(0, 60)}</code>
                </p>
              )
            ),
          )}
          {error && <pre className="sql-error">{error}</pre>}
        </div>
      </div>
      <p className="small muted playground-note">{t("sql.freshDb")}</p>
    </div>
  );
}
