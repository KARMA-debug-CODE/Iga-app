import { useEffect, useLayoutEffect, useRef, useState } from "react";

import { useI18n } from "../i18n";
import CodeEditor from "./CodeEditor";
import { Icon } from "./Icon";

// The preview page (public/playground-frame.html). It has its own Content-Security-Policy: a srcdoc frame
// would inherit the app's, which blocks the inline scripts students write.
const FRAME_URL = "/playground-frame.html";

/** The sandboxed preview: a fresh page for each run, which gets the student's code once it is ready. */
function Preview({ html, title, height }) {
  const frame = useRef(null);
  // Listening from the commit itself, before the new page can load and say it is ready.
  useLayoutEffect(() => {
    function onMessage(event) {
      if (event.source !== frame.current?.contentWindow || event.data?.type !== "iga-playground-ready") return;
      // The sandboxed page has no origin of its own ("null"), so "*" is the only target that reaches it.
      event.source.postMessage({ type: "iga-playground", html }, "*");
    }
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [html]);
  return <iframe ref={frame} title={title} sandbox="allow-scripts allow-modals" src={FRAME_URL} style={{ minHeight: height }} />;
}

/**
 * A W3Schools-style "Try it yourself" editor. The preview runs in a sandboxed
 * iframe (scripts allowed, but no access to this page, cookies or storage).
 */
export default function CodePlayground({ initialCode = "", height = 320 }) {
  const { t } = useI18n();
  const [code, setCode] = useState(initialCode);
  const [rendered, setRendered] = useState(initialCode);
  // Each run loads a fresh preview page, as a new srcdoc did.
  const [run, setRun] = useState(0);
  const [autoRun, setAutoRun] = useState(false);
  const show = (html) => {
    setRendered(html);
    setRun((n) => n + 1);
  };

  useEffect(() => {
    if (!autoRun) return undefined;
    const id = setTimeout(() => {
      setRendered(code);
      setRun((n) => n + 1);
    }, 400);
    return () => clearTimeout(id);
  }, [code, autoRun]);

  return (
    <div className="playground">
      <div className="playground-bar">
        <strong className="playground-title">
          <Icon name="code" /> HTML · CSS · JS
        </strong>
        <label className="check small">
          <input type="checkbox" checked={autoRun} onChange={(e) => setAutoRun(e.target.checked)} />
          {t("common.autoRun")}
        </label>
        <button className="btn btn-sm btn-secondary" onClick={() => { setCode(initialCode); show(initialCode); }}>
          <Icon name="reset" /> {t("common.reset")}
        </button>
        <button className="btn btn-sm btn-success" onClick={() => show(code)}>
          <Icon name="play" /> {t("common.run")}
        </button>
      </div>
      <div className="playground-panes">
        <CodeEditor value={code} onChange={setCode} language="html" onRun={() => show(code)} ariaLabel={t("a11y.codeEditor")} minHeight={height} />
        <Preview key={run} html={rendered} title={t("a11y.preview")} height={height} />
      </div>
    </div>
  );
}
