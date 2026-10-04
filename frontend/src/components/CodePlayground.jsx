import { useEffect, useState } from "react";

import { useI18n } from "../i18n";

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

  function onKeyDown(event) {
    // Tab inserts two spaces instead of leaving the editor.
    if (event.key === "Tab" && !event.shiftKey) {
      event.preventDefault();
      const el = event.currentTarget;
      const { selectionStart: start, selectionEnd: end } = el;
      const next = `${code.slice(0, start)}  ${code.slice(end)}`;
      setCode(next);
      requestAnimationFrame(() => {
        el.selectionStart = el.selectionEnd = start + 2;
      });
    }
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      setRendered(code);
    }
  }

  return (
    <div className="playground">
      <div className="playground-bar">
        <strong style={{ marginRight: "auto" }}>💻 HTML · CSS · JS</strong>
        <label className="check small">
          <input type="checkbox" checked={autoRun} onChange={(e) => setAutoRun(e.target.checked)} />
          {t("common.autoRun")}
        </label>
        <button className="btn btn-sm btn-secondary" onClick={() => { setCode(initialCode); setRendered(initialCode); }}>
          {t("common.reset")}
        </button>
        <button className="btn btn-sm btn-success" onClick={() => setRendered(code)}>
          ▶ {t("common.run")}
        </button>
      </div>
      <div className="playground-panes">
        <textarea
          value={code}
          onChange={(e) => setCode(e.target.value)}
          onKeyDown={onKeyDown}
          spellCheck={false}
          autoCapitalize="off"
          autoCorrect="off"
          aria-label={t("a11y.codeEditor")}
          style={{ minHeight: height }}
        />
        <iframe title={t("a11y.preview")} sandbox="allow-scripts allow-modals" srcDoc={rendered} style={{ minHeight: height }} />
      </div>
    </div>
  );
}
