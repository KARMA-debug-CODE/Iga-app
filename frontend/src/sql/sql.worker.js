// Runs student SQL with SQLite compiled to WebAssembly (sql.js), off the main thread so a runaway
// query can't freeze the page (the UI stops it by terminating this worker). Each run starts from an
// empty in-memory database, like running a script. A classic worker: sql.js is a classic script.
/* global importScripts, initSqlJs */

const MAX_ROWS = 200; // rows shown per result; more are counted but not sent

let ready = null;

// Rows inserted, updated or deleted so far (getRowsModified() repeats the last count after a CREATE).
function totalChanges(db) {
  return db.exec("SELECT total_changes()")[0].values[0][0];
}

function load() {
  ready ??= (async () => {
    const base = `${self.location.origin}/runtimes/sqljs/`;
    importScripts(`${base}sql-wasm-browser.js`);
    return initSqlJs({ locateFile: (file) => `${base}${file}` });
  })();
  return ready;
}

self.onmessage = async ({ data }) => {
  if (data.type !== "run") return;
  let SQL;
  try {
    SQL = await load();
  } catch (err) {
    ready = null;
    self.postMessage({ type: "error", code: "start-failed", detail: String(err?.message || err) });
    return;
  }
  self.postMessage({ type: "started" });
  const db = new SQL.Database();
  const results = [];
  try {
    // One statement at a time, so a SELECT in the middle of the script shows its own table
    // and an error names the statement that failed.
    for (const statement of db.iterateStatements(data.code)) {
      // The statement without the comments and blank lines before it.
      const sql = statement
        .getSQL()
        .split("\n")
        .filter((line) => line.trim() && !line.trim().startsWith("--"))
        .join("\n");
      const columns = statement.getColumnNames();
      const before = totalChanges(db);
      const rows = [];
      let total = 0;
      while (statement.step()) {
        total += 1;
        if (rows.length < MAX_ROWS) rows.push(statement.get());
      }
      const changed = totalChanges(db) - before; // the iterator frees each statement itself
      if (columns.length) results.push({ sql, columns, rows, total });
      else results.push({ sql, changed });
    }
    self.postMessage({ type: "done", results });
  } catch (err) {
    self.postMessage({ type: "done", results, error: String(err?.message || err) });
  } finally {
    db.close();
  }
};
