import { describe, expect, it } from "vitest";

import { BLOCKED, lockDown } from "./lockdown";

function fakeWorkerScope() {
  // Like a worker's global scope: its own properties, and a navigator whose getters live on a prototype.
  const scope = Object.fromEntries(BLOCKED.map((name) => [name, () => name]));
  scope.postMessage = () => {};
  const WorkerNavigator = { get serviceWorker() { return {}; }, get storage() { return {}; }, userAgent: "test" };
  scope.navigator = Object.create(WorkerNavigator);
  return scope;
}

describe("Python worker lockdown", () => {
  it("takes away the network, the offline data and new workers", () => {
    const scope = fakeWorkerScope();
    expect(lockDown(scope)).toEqual([]);
    for (const name of BLOCKED) expect(scope[name]).toBeUndefined();
    expect(scope.navigator.serviceWorker).toBeUndefined();
    expect(scope.navigator.storage).toBeUndefined();
    // What programs need stays.
    expect(typeof scope.postMessage).toBe("function");
    expect(scope.navigator.userAgent).toBe("test");
  });

  it("names what it could not take away, so the worker refuses to run programs", () => {
    const scope = fakeWorkerScope();
    Object.defineProperty(scope, "fetch", { value: () => "fetch", configurable: false, writable: false });
    expect(lockDown(scope)).toEqual(["fetch"]);
  });

  it("covers this browser's real globals", () => {
    // jsdom's window has some of these; whatever exists here is removable the same way.
    const names = ["fetch", "XMLHttpRequest", "WebSocket", "EventSource", "Worker", "SharedWorker", "caches", "indexedDB"];
    expect(BLOCKED).toEqual(expect.arrayContaining(names));
  });
});
