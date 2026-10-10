// The code editor itself (CodeMirror 6): automatic indentation, syntax colours, line numbers, matching
// brackets and completion, like a real editor. Loaded on demand by CodeEditor.jsx.
import { autocompletion, closeBrackets, closeBracketsKeymap, completionKeymap } from "@codemirror/autocomplete";
import { defaultKeymap, history, historyKeymap, indentWithTab } from "@codemirror/commands";
import { bracketMatching, indentOnInput, indentUnit } from "@codemirror/language";
import { Compartment, EditorState } from "@codemirror/state";
import { oneDark } from "@codemirror/theme-one-dark";
import { drawSelection, EditorView, highlightActiveLine, highlightActiveLineGutter, keymap, lineNumbers } from "@codemirror/view";
import { useEffect, useRef } from "react";

// Each language's grammar is downloaded only when an editor for it opens.
const LANGUAGES = {
  python: () => import("@codemirror/lang-python").then((m) => m.python()),
  cpp: () => import("@codemirror/lang-cpp").then((m) => m.cpp()),
  java: () => import("@codemirror/lang-java").then((m) => m.java()),
  sql: () => import("@codemirror/lang-sql").then((m) => m.sql()),
  html: () => import("@codemirror/lang-html").then((m) => m.html()),
};

export default function CodeMirrorEditor({ value, onChange, language, onRun, ariaLabel, minHeight = 300 }) {
  const host = useRef(null);
  const view = useRef(null);
  const latest = useRef({ onChange, onRun });

  useEffect(() => {
    latest.current = { onChange, onRun };
  }, [onChange, onRun]);

  useEffect(() => {
    const grammar = new Compartment();
    const editor = new EditorView({
      parent: host.current,
      state: EditorState.create({
        doc: value,
        extensions: [
          lineNumbers(),
          highlightActiveLineGutter(),
          highlightActiveLine(),
          history(),
          drawSelection(),
          indentOnInput(), // e.g. "}" or "else:" moves back to the right column as it is typed
          bracketMatching(),
          closeBrackets(),
          autocompletion(),
          indentUnit.of(language === "html" ? "  " : "    "),
          EditorState.tabSize.of(4),
          keymap.of([
            { key: "Mod-Enter", run: () => (latest.current.onRun?.(), true) },
            ...closeBracketsKeymap,
            ...completionKeymap,
            ...defaultKeymap, // Enter keeps the indentation and adds a level after ":" or "{"
            ...historyKeymap,
            indentWithTab, // Tab / Shift+Tab indent and outdent (Esc, then Tab, leaves the editor)
          ]),
          grammar.of([]),
          oneDark,
          EditorView.updateListener.of((update) => {
            if (update.docChanged) latest.current.onChange?.(update.state.doc.toString());
          }),
          EditorView.contentAttributes.of({
            "aria-label": ariaLabel,
            autocapitalize: "off",
            autocorrect: "off",
            spellcheck: "false",
          }),
          EditorView.theme({
            "&": { minHeight: `${minHeight}px`, height: "100%", fontSize: "0.9rem" },
            ".cm-scroller": { fontFamily: "var(--mono)", lineHeight: "1.55" },
          }),
        ],
      }),
    });
    view.current = editor;
    let alive = true;
    LANGUAGES[language]?.()
      .then((support) => alive && editor.dispatch({ effects: grammar.reconfigure(support) }))
      .catch(() => {}); // offline before the grammar was saved: the editor still works, without colours
    return () => {
      alive = false;
      editor.destroy();
    };
    // The editor is created once per language; later text changes from outside arrive below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [language]);

  // Text replaced from outside the editor (Reset, a new starter program).
  useEffect(() => {
    const editor = view.current;
    if (editor && editor.state.doc.toString() !== value) {
      editor.dispatch({ changes: { from: 0, to: editor.state.doc.length, insert: value } });
    }
  }, [value]);

  return <div ref={host} className="code-editor" />;
}
