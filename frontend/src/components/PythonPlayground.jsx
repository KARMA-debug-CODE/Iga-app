import { useEffect, useRef, useState } from "react";

import { useI18n } from "../i18n";

function newWorker() {
  return new Worker(new URL("../python/pyodide.worker.js", import.meta.url), { type: "module" });
}

/** A "try it yourself" Python editor. Python runs in the browser (Pyodide), so no server is involved. */
export default function PythonPlayground({ initialCode = "", height = 300 }) {
  const { t } = useI18n();
  const [code, setCode] = useState(initialCode);
  const [stdin, setStdin] = useState("");
  const [showInput, setShowInput] = useState(/input\(/.test(initialCode));
  const [output, setOutput] = useState([]);
  const [status, setStatus] = useState("idle"); // idle | loading | running
  const worker = useRef(null);
  const loadedOnce = useRef(false);

  useEffect(() => () => worker.current?.terminate(), []);

  function append(stream, text) {
    setOutput((o) => [...o, { stream, text }]);
  }

  function run() {
    if (!worker.current) {
      worker.current = newWorker();
      worker.current.onmessage = ({ data }) => {
        if (data.type === "started") {
          loadedOnce.current = true;
          setStatus("running");
        } else if (data.type === "out") {
          append(data.stream, data.text);
        } else if (data.type === "done") {
          if (data.result !== null) append("result", data.result);
          setStatus("idle");
        } else if (data.type === "error") {
          append("stderr", data.text);
          setStatus("idle");
        }
      };
      worker.current.onerror = (event) => {
        append("stderr", event.message || "Python stopped unexpectedly.");
        worker.current?.terminate();
        worker.current = null;
        setStatus("idle");
      };
    }
    setOutput([]);
    setStatus(loadedOnce.current ? "running" : "loading");
    worker.current.postMessage({ type: "run", code, stdin });
  }

  function stop() {
    worker.current?.terminate();
    worker.current = null;
    loadedOnce.current = false;
    append("stderr", `⏹ ${t("python.stopped")}`);
    setStatus("idle");
  }

  const busy = status !== "idle";

  return (
    <div className="playground python-playground">
      <div className="playground-bar">
        <strong style={{ marginRight: "auto" }}>🐍 Python</strong>
        <button className="btn btn-sm btn-ghost" onClick={() => setShowInput((v) => !v)} aria-pressed={showInput}>
          ⌨ {t("python.input")}
        </button>
        <button
          className="btn btn-sm btn-secondary"
          onClick={() => {
            setCode(initialCode);
            setOutput([]);
          }}
          disabled={busy}
        >
          {t("common.reset")}
        </button>
        {busy ? (
          <button className="btn btn-sm btn-danger" onClick={stop}>
            ⏹ {t("python.stop")}
          </button>
        ) : (
          <button className="btn btn-sm btn-success" onClick={run}>
            ▶ {t("common.run")}
          </button>
        )}
      </div>
      <div className="playground-panes">
        <textarea
          value={code}
          onChange={(e) => setCode(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Tab" && !e.shiftKey) {
              e.preventDefault();
              const el = e.currentTarget;
              const { selectionStart: s, selectionEnd: end } = el;
              setCode(`${code.slice(0, s)}    ${code.slice(end)}`);
              requestAnimationFrame(() => {
                el.selectionStart = el.selectionEnd = s + 4;
              });
            }
            if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && !busy) run();
          }}
          spellCheck={false}
          autoCapitalize="off"
          autoCorrect="off"
          aria-label="Python code editor"
          style={{ minHeight: height }}
        />
        <div className="python-output-wrap">
          {showInput && (
            <label className="python-stdin">
              <span className="small">{t("python.inputHelp")}</span>
              <textarea value={stdin} onChange={(e) => setStdin(e.target.value)} rows={3} spellCheck={false} />
            </label>
          )}
          <pre className="python-output" aria-live="polite" style={{ minHeight: height }}>
            {status === "loading" && <span className="muted">{t("python.loading")}</span>}
            {output.map((line, i) => (
              <span key={i} className={`py-${line.stream}`}>
                {line.text}
                {"\n"}
              </span>
            ))}
            {status === "idle" && output.length === 0 && <span className="muted">{t("python.empty")}</span>}
          </pre>
        </div>
      </div>
    </div>
  );
}
