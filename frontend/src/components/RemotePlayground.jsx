import { useEffect, useRef, useState } from "react";

import { api, NetworkError } from "../api";
import { useOnline } from "../hooks";
import { useI18n } from "../i18n";
import CodeEditor from "./CodeEditor";
import Console from "./Console";
import { Icon } from "./Icon";

const NAMES = { cpp: "C++", java: "Java" };

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
 * A C++ or Java editor with a terminal. The program is compiled and run on the Iga server's code runner; when
 * it waits for keyboard input (cin, Scanner), the console shows the question and the student types the answer,
 * as in a real terminal. Each step sends only the code or the answer (a few KB).
 */
export default function RemotePlayground({ language, initialCode = "", height = 300 }) {
  const { t } = useI18n();
  const online = useOnline();
  const enabled = useCodeRunnerEnabled();
  const [code, setCode] = useState(initialCode);
  const [output, setOutput] = useState([]);
  const [state, setState] = useState("idle"); // idle | running | waiting
  const session = useRef(null);
  const name = NAMES[language];

  // Leaving the page ends a program that is still waiting for an answer.
  useEffect(
    () => () => {
      if (session.current) api("/code/stop/", { method: "POST", body: { session: session.current } }).catch(() => {});
    },
    [],
  );

  function append(entries) {
    setOutput((o) => [...o, ...entries]);
  }

  function explain(result) {
    const lines = {
      ok: t("code.finished"),
      compile_error: t("code.compileError"),
      time_limit: t("code.timeLimit"),
      output_limit: t("code.outputLimit"),
      runtime_error:
        result.signal === "SIGSEGV"
          ? t("code.crashed")
          : t("code.runtimeError", { code: result.exit_code ?? result.signal ?? "?" }),
    };
    return lines[result.verdict] || t("code.runtimeError", { code: result.exit_code ?? "?" });
  }

  function handle(result) {
    append(result.output || []);
    if (result.state === "waiting") {
      session.current = result.session;
      setState("waiting");
      return;
    }
    session.current = null;
    const javaMainHint = language === "java" && result.verdict === "runtime_error" && /main\(String\[\]\)|main method/i.test(
      (result.output || []).map((o) => o.text).join(""),
    );
    append([{ stream: result.verdict === "ok" ? "info" : "stderr", text: `\n${explain(result)}` }]);
    if (javaMainHint) append([{ stream: "info", text: `\n${t("code.javaMainHint")}` }]);
    setState("idle");
  }

  function fail(err) {
    session.current = null;
    append([{ stream: "stderr", text: `\n${err instanceof NetworkError ? t("code.offline") : err.message}` }]);
    setState("idle");
  }

  async function run() {
    if (state !== "idle" || !code.trim()) return;
    setOutput([]);
    setState("running");
    try {
      handle(await api("/code/run/", { method: "POST", body: { language, code } }));
    } catch (err) {
      fail(err);
    }
  }

  async function answer(text) {
    append([{ stream: "stdin", text: `${text}\n` }]);
    setState("running");
    try {
      handle(await api("/code/input/", { method: "POST", body: { session: session.current, text } }));
    } catch (err) {
      fail(err);
    }
  }

  function stop() {
    const id = session.current;
    session.current = null;
    if (id) api("/code/stop/", { method: "POST", body: { session: id } }).catch(() => {});
    append([{ stream: "stderr", text: `\n${t("python.stopped")}` }]);
    setState("idle");
  }

  return (
    <div className="playground remote-playground">
      <div className="playground-bar">
        <strong className="playground-title">
          <Icon name="code" /> {name}
        </strong>
        <button
          className="btn btn-sm btn-secondary"
          onClick={() => {
            setCode(initialCode);
            setOutput([]);
          }}
          disabled={state !== "idle"}
        >
          <Icon name="reset" /> {t("common.reset")}
        </button>
        {state === "waiting" ? (
          <button className="btn btn-sm btn-danger" onClick={stop}>
            <Icon name="stop" /> {t("python.stop")}
          </button>
        ) : (
          <button className="btn btn-sm btn-success" onClick={run} disabled={state !== "idle" || enabled === false || !code.trim()}>
            <Icon name="play" /> {state === "running" ? t("code.running") : t("common.run")}
          </button>
        )}
      </div>
      {enabled === false && <p className="alert alert-warn playground-alert">{t("code.notConfigured")}</p>}
      {enabled !== false && !online && <p className="alert alert-warn playground-alert">{t("code.offline")}</p>}
      <div className="playground-panes">
        <CodeEditor value={code} onChange={setCode} language={language} onRun={run} ariaLabel={t("code.editor", { language: name })} minHeight={height} />
        <Console
          entries={output}
          waiting={state === "waiting"}
          onAnswer={answer}
          status={state === "running" && !output.length ? t("code.runningOnServer") : ""}
          empty={t("code.empty")}
          minHeight={height}
          label={t("console.output")}
        />
      </div>
      <p className="small muted playground-note">{t("code.serverNote", { language: name })}</p>
    </div>
  );
}
