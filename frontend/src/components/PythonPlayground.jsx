import { useEffect, useRef, useState } from "react";

import { useI18n } from "../i18n";
import CodeEditor from "./CodeEditor";
import Console from "./Console";
import { Icon } from "./Icon";

function newWorker() {
  return new Worker(new URL("../python/pyodide.worker.js", import.meta.url), { type: "module" });
}

// Browsers with JavaScript Promise Integration let input() pause the program and wait for typing.
const INTERACTIVE = typeof WebAssembly !== "undefined" && typeof WebAssembly.Suspending === "function";

/** A "try it yourself" Python editor. Python runs in the browser (Pyodide), so no server is involved. */
export default function PythonPlayground({ initialCode = "", height = 300 }) {
  const { t } = useI18n();
  const [code, setCode] = useState(initialCode);
  const [stdin, setStdin] = useState("");
  const [showInput, setShowInput] = useState(!INTERACTIVE && /input\(/.test(initialCode));
  const [output, setOutput] = useState([]);
  const [status, setStatus] = useState("idle"); // idle | loading | running | waiting
  const worker = useRef(null);
  const loadedOnce = useRef(false);
  const tr = useRef(t); // the worker's handlers outlive renders, so they read the current language from here

  useEffect(() => () => worker.current?.terminate(), []);
  useEffect(() => {
    tr.current = t;
  }, [t]);

  function append(stream, text) {
    setOutput((o) => [...o, { stream, text }]);
  }

  function run() {
    if (status !== "idle") return;
    if (!worker.current) {
      worker.current = newWorker();
      worker.current.onmessage = ({ data }) => {
        if (data.type === "started") {
          loadedOnce.current = true;
          setStatus("running");
        } else if (data.type === "out") {
          append(data.stream, data.text);
        } else if (data.type === "input") {
          setStatus("waiting");
        } else if (data.type === "done") {
          if (data.result !== null) append("result", `${data.result}\n`);
          append("info", `\n${tr.current("code.finished")}`);
          setStatus("idle");
        } else if (data.type === "error") {
          append("stderr", data.code === "start-failed" ? tr.current("python.startFailed", { error: data.detail }) : data.text);
          setStatus("idle");
        }
      };
      worker.current.onerror = (event) => {
        append("stderr", event.message || tr.current("python.crashed"));
        worker.current?.terminate();
        worker.current = null;
        setStatus("idle");
      };
    }
    setOutput([]);
    setStatus(loadedOnce.current ? "running" : "loading");
    worker.current.postMessage({ type: "run", code, stdin });
  }

  function answer(text) {
    append("stdin", `${text}\n`);
    setStatus("running");
    worker.current?.postMessage({ type: "stdin", text });
  }

  function stop() {
    worker.current?.terminate();
    worker.current = null;
    loadedOnce.current = false;
    append("stderr", `\n${t("python.stopped")}`);
    setStatus("idle");
  }

  const busy = status !== "idle";

  return (
    <div className="playground python-playground">
      <div className="playground-bar">
        <strong className="playground-title">
          <Icon name="python" /> Python
        </strong>
        {!INTERACTIVE && (
          <button className="btn btn-sm btn-ghost" onClick={() => setShowInput((v) => !v)} aria-pressed={showInput}>
            <Icon name="keyboard" /> {t("python.input")}
          </button>
        )}
        <button
          className="btn btn-sm btn-secondary"
          onClick={() => {
            setCode(initialCode);
            setOutput([]);
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
        <CodeEditor value={code} onChange={setCode} language="python" onRun={run} ariaLabel={t("python.editor")} minHeight={height} />
        <div className="python-output-wrap">
          {showInput && (
            <label className="python-stdin">
              <span className="small">{t("python.inputHelp")}</span>
              <textarea value={stdin} onChange={(e) => setStdin(e.target.value)} rows={3} spellCheck={false} />
            </label>
          )}
          <Console
            entries={output}
            waiting={status === "waiting"}
            onAnswer={answer}
            status={status === "loading" ? t("python.loading") : ""}
            empty={t("python.empty")}
            minHeight={height}
            label={t("console.output")}
          />
        </div>
      </div>
    </div>
  );
}
