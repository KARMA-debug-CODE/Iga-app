// What a Python program can't reach from its worker.
//
// The worker has this site's origin, and the program may come from a lesson a teacher wrote ("python-run"
// blocks). Python reaches every JavaScript global through `import js`, so with fetch or XMLHttpRequest a
// program could POST to /api/auth/refresh/ (the browser adds the student's sign-in cookie) and act as the
// student; with the Cache API or IndexedDB it could read the app's offline copies of their data; a new
// Worker or SharedWorker would have all of these again. Pyodide looks these names up each time it uses
// them and keeps no copy, so once it has loaded its files they can be taken away. No student program
// needs the network.
export const BLOCKED = [
  "fetch",
  "XMLHttpRequest",
  "WebSocket",
  "WebTransport",
  "EventSource",
  "Worker",
  "SharedWorker",
  "importScripts",
  "caches",
  "indexedDB",
  "BroadcastChannel",
];
const BLOCKED_ON_NAVIGATOR = ["serviceWorker", "storage"];

function remove(target, name) {
  try {
    delete target[name];
  } catch {
    // not configurable: shadowed below if possible
  }
  if (target[name] === undefined) return;
  try {
    // Still there (from a prototype): an own property hides it.
    Object.defineProperty(target, name, { value: undefined, writable: false, configurable: false });
  } catch {
    // reported by lockDown's answer
  }
}

/** Remove the names above from `scope`. Returns the names still reachable (empty when locked down). */
export function lockDown(scope = globalThis) {
  for (const name of BLOCKED) remove(scope, name);
  const navigator = scope.navigator;
  if (navigator) for (const name of BLOCKED_ON_NAVIGATOR) remove(navigator, name);
  return [
    ...BLOCKED.filter((name) => scope[name] !== undefined),
    ...(navigator ? BLOCKED_ON_NAVIGATOR.filter((name) => navigator[name] !== undefined).map((name) => `navigator.${name}`) : []),
  ];
}
