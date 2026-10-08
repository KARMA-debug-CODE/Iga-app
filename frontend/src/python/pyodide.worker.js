// Runs student Python code with Pyodide, off the main thread so an infinite loop can't freeze the page
// (the UI stops it by terminating this worker).
//
// input() works like in a real terminal: the prompt is shown, the program pauses, and it carries on with
// what the student types in the console. This uses JavaScript Promise Integration (JSPI, in current
// Chrome, Edge and Android browsers). Where the browser lacks it, input() reads the lines typed in the
// Input box before Run instead.

let runtime = null;
let stdinLines = [];
let answer = null; // resolves the pending input() with the student's answer

const INTERACTIVE = typeof WebAssembly !== "undefined" && typeof WebAssembly.Suspending === "function";
const pending = { stdout: "", stderr: "" };
const decoders = { stdout: new TextDecoder(), stderr: new TextDecoder() };

function flush(stream) {
  if (pending[stream]) {
    self.postMessage({ type: "out", stream, text: pending[stream] });
    pending[stream] = "";
  }
}

function writer(stream) {
  return {
    isatty: true, // line-buffered, like a terminal
    write(buffer) {
      pending[stream] += decoders[stream].decode(buffer, { stream: true });
      if (pending[stream].includes("\n") || pending[stream].length > 2048) flush(stream);
      return buffer.length;
    },
  };
}

// Called from Python's input(): show what was printed so far, then wait for the student's answer.
self.igaReadLine = () => {
  flush("stderr");
  flush("stdout");
  self.postMessage({ type: "input" });
  return new Promise((resolve) => {
    answer = resolve;
  });
};

const PRELUDE = `
import builtins, sys
from pyodide.ffi import can_run_sync, run_sync
import js

_iga_original_input = builtins.input

def _iga_input(prompt=""):
    if not can_run_sync():
        return _iga_original_input(prompt)
    sys.stdout.write(str(prompt))
    sys.stdout.flush()
    return run_sync(js.igaReadLine())

builtins.input = _iga_input
`;

function load() {
  runtime ??= (async () => {
    const base = `${self.location.origin}/pyodide/`;
    const { loadPyodide } = await import(/* @vite-ignore */ `${base}pyodide.mjs`);
    const pyodide = await loadPyodide({ indexURL: base });
    pyodide.setStdout(writer("stdout"));
    pyodide.setStderr(writer("stderr"));
    // Without JSPI, input() reads the lines typed in the "Input" box; EOF after the last line.
    pyodide.setStdin({ stdin: () => (stdinLines.length ? stdinLines.shift() : null) });
    pyodide.runPython(PRELUDE);
    return pyodide;
  })();
  return runtime;
}

function cleanTraceback(message) {
  // Hide Pyodide's own frames so students only see their code's error.
  const lines = String(message).split("\n");
  const start = lines.findIndex((l) => l.includes('File "<exec>"'));
  if (start === -1) return message;
  return ["Traceback (most recent call last):", ...lines.slice(start)].join("\n");
}

self.onmessage = async ({ data }) => {
  if (data.type === "stdin") {
    const resolve = answer;
    answer = null;
    resolve?.(String(data.text));
    return;
  }
  if (data.type !== "run") return;
  let pyodide;
  try {
    pyodide = await load();
  } catch (err) {
    runtime = null;
    const detail = String(err?.message || err);
    self.postMessage({ type: "error", code: "start-failed", detail, text: `Could not start Python: ${detail}` });
    return;
  }
  self.postMessage({ type: "started", interactive: INTERACTIVE });
  stdinLines = data.stdin ? String(data.stdin).split("\n") : [];
  const globals = pyodide.globals.get("dict")();
  try {
    const result = await pyodide.runPythonAsync(data.code, { globals, filename: "<exec>" });
    const shown = result === undefined || result === null ? null : String(result);
    if (result && typeof result.destroy === "function") result.destroy();
    flush("stdout");
    flush("stderr");
    self.postMessage({ type: "done", result: shown });
  } catch (err) {
    flush("stdout");
    flush("stderr");
    self.postMessage({ type: "error", text: cleanTraceback(err?.message || err) });
  } finally {
    globals.destroy();
  }
};

self.postMessage({ type: "hello", interactive: INTERACTIVE });
