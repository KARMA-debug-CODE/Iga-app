import { lazy, Suspense } from "react";

const CodeMirrorEditor = lazy(() => import("./CodeMirrorEditor"));

/**
 * A code editor with automatic indentation and syntax colours. While the editor's code downloads (the
 * first time only) a plain text box is shown, so the student can start typing at once.
 */
export default function CodeEditor({ value, onChange, language, onRun, ariaLabel, minHeight = 300 }) {
  const fallback = (
    <textarea
      className="code-editor-fallback"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onKeyDown={(e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === "Enter") onRun?.();
      }}
      spellCheck={false}
      autoCapitalize="off"
      autoCorrect="off"
      aria-label={ariaLabel}
      style={{ minHeight }}
    />
  );
  return (
    <Suspense fallback={fallback}>
      <CodeMirrorEditor value={value} onChange={onChange} language={language} onRun={onRun} ariaLabel={ariaLabel} minHeight={minHeight} />
    </Suspense>
  );
}
