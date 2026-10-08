import { useEffect, useState } from "react";

import { useI18n } from "../i18n";
import CodeEditor from "./CodeEditor";
import { Icon } from "./Icon";

/**
 * A W3Schools-style "Try it yourself" editor. The preview runs in a sandboxed
 * iframe (scripts allowed, but no access to this page, cookies or storage).
 */
export default function CodePlayground({ initialCode = "", height = 320 }) {
  const { t } = useI18n();
  const [code, setCode] = useState(initialCode);
  const [rendered, setRendered] = useState(initialCode);
  const [autoRun, setAutoRun] = useState(false);

  useEffect(() => {
    if (!autoRun) return undefined;
    const id = setTimeout(() => setRendered(code), 400);
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
        <button className="btn btn-sm btn-secondary" onClick={() => { setCode(initialCode); setRendered(initialCode); }}>
          <Icon name="reset" /> {t("common.reset")}
        </button>
        <button className="btn btn-sm btn-success" onClick={() => setRendered(code)}>
          <Icon name="play" /> {t("common.run")}
        </button>
      </div>
      <div className="playground-panes">
        <CodeEditor value={code} onChange={setCode} language="html" onRun={() => setRendered(code)} ariaLabel={t("a11y.codeEditor")} minHeight={height} />
        <iframe title={t("a11y.preview")} sandbox="allow-scripts allow-modals" srcDoc={rendered} style={{ minHeight: height }} />
      </div>
    </div>
  );
}
