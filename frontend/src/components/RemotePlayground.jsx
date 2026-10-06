import { useEffect, useState } from "react";

import { api, NetworkError } from "../api";
import { useOnline } from "../hooks";
import { useI18n } from "../i18n";

const NAMES = { cpp: "C++", java: "Java" };
const ICONS = { cpp: "⚙️", java: "☕" };

let statusRequest = null;

/** Whether this server has a code runner for C++ and Java (asked once per page load). */
function useCodeRunnerEnabled() {
  const [enabled, setEnabled] = useState(null);
  useEffect(() => {
    statusRequest ??= api("/code/status/")
      .then((s) => Boolean(s?.enabled))
      .catch(() => {
        statusRequest = null; // ask again next time, e.g. once back online
        return true; // assume it is there; a run will say otherwise
      });
    let alive = true;
    statusRequest.then((value) => alive && setEnabled(value));
    return () => {
      alive = false;
    };
  }, []);
  return enabled;
}

/**
 * A C++ or Java editor. Unlike Python and SQL, these are compiled and run on the Iga server's sandboxed
 * code runner, so they need a connection; each run sends only the code and the input (a few KB).
 */
export default function RemotePlayground({ language, initialCode = "", initialInput = "", height = 300 }) {
  const { t } = useI18n();
  const online = useOnline();
  const enabled = useCodeRunnerEnabled();
  const [code, setCode] = useState(initialCode);
  const [stdin, setStdin] = useState(initialInput);
  const [showInput, setShowInput] = useState(Boolean(initialInput));
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const name = NAMES[language];

  async function run() {
    if (busy) return;
    setBusy(true);
    setResult(null);
    setError(null);
    try {
      setResult(await api("/code/run/", { method: "POST", body: { language, code, stdin } }));
    } catch (err) {
      setError(err instanceof NetworkError ? new Error(t("code.offline")) : err);
    } finally {
      setBusy(false);
    }
  }

  const compileOutput = result?.compile && (result.compile.stderr || result.compile.stdout);
  const notice = {
    compile_error: t("code.compileError"),
    compile_time_limit: t("code.compileTimeLimit"),
    time_limit: t("code.timeLimit"),
    output_limit: t("code.outputLimit"),
    killed: t("code.killed"),
    runtime_error: t("code.runtimeError", { code: result?.run?.code ?? "?" }),
  }[result?.verdict];
  const javaMainHint =
    language === "java" && result?.verdict === "runtime_error" && /main\(String\[\]\)|no main method/i.test(result.run?.stderr || "");

  return (
    <div className="playground remote-playground">
      <div className="playground-bar">
        <strong style={{ marginRight: "auto" }}>
          {ICONS[language]} {name}
        </strong>
        <button className="btn btn-sm btn-ghost" onClick={() => setShowInput((v) => !v)} aria-pressed={showInput}>
          ⌨ {t("python.input")}
        </button>
        <button
          className="btn btn-sm btn-secondary"
          onClick={() => {
            setCode(initialCode);
            setStdin(initialInput);
            setResult(null);
            setError(null);
          }}
          disabled={busy}
        >
          {t("common.reset")}
        </button>
        <button className="btn btn-sm btn-success" onClick={run} disabled={busy || enabled === false || !code.trim()}>
          ▶ {busy ? t("code.running") : t("common.run")}
        </button>
      </div>
      {enabled === false && <p className="alert alert-warn playground-alert">{t("code.notConfigured")}</p>}
      {enabled !== false && !online && <p className="alert alert-warn playground-alert">{t("code.offline")}</p>}
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
            if ((e.ctrlKey || e.metaKey) && e.key === "Enter") run();
          }}
          spellCheck={false}
          autoCapitalize="off"
          autoCorrect="off"
          aria-label={t("code.editor", { language: name })}
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
            {busy && <span className="muted">{t("code.runningOnServer")}</span>}
            {!busy && !result && !error && <span className="muted">{t("code.empty")}</span>}
            {error && <span className="py-stderr">{error.message}</span>}
            {notice && (
              <span className="py-stderr">
                {notice}
                {"\n"}
              </span>
            )}
            {compileOutput && <span className="py-stderr">{compileOutput}</span>}
            {result?.run?.stdout && <span className="py-stdout">{result.run.stdout}</span>}
            {result?.run?.stderr && <span className="py-stderr">{result.run.stderr}</span>}
            {javaMainHint && (
              <span className="py-result">
                {"\n"}💡 {t("code.javaMainFirst")}
              </span>
            )}
            {result?.verdict === "ok" && <span className="muted">{`\n✓ ${t("code.finished")}`}</span>}
          </pre>
        </div>
      </div>
      <p className="small muted playground-note">{t("code.serverNote", { language: name })}</p>
    </div>
  );
}
