// Runs student Python code with Pyodide, off the main thread so an infinite loop
// can't freeze the page (the UI stops it by terminating this worker).

let runtime = null;
let stdinLines = [];

function load() {
  runtime ??= (async () => {
    const base = `${self.location.origin}/pyodide/`;
    const { loadPyodide } = await import(/* @vite-ignore */ `${base}pyodide.mjs`);
    const pyodide = await loadPyodide({ indexURL: base });
    pyodide.setStdout({ batched: (text) => self.postMessage({ type: "out", stream: "stdout", text }) });
    pyodide.setStderr({ batched: (text) => self.postMessage({ type: "out", stream: "stderr", text }) });
    // input() reads from the lines typed in the "Input" box; EOF after the last line.
    pyodide.setStdin({ stdin: () => (stdinLines.length ? stdinLines.shift() : null) });
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
  self.postMessage({ type: "started" });
  stdinLines = data.stdin ? String(data.stdin).split("\n") : [];
  const globals = pyodide.globals.get("dict")();
  try {
    const result = await pyodide.runPythonAsync(data.code, { globals, filename: "<exec>" });
    const shown = result === undefined || result === null ? null : String(result);
    if (result && typeof result.destroy === "function") result.destroy();
    self.postMessage({ type: "done", result: shown });
  } catch (err) {
    self.postMessage({ type: "error", text: cleanTraceback(err?.message || err) });
  } finally {
    globals.destroy();
  }
};
