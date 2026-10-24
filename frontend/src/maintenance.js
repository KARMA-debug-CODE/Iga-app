// Maintenance mode: the server answers 503 {"code": "maintenance"} to everyone but the Iga team while Iga is
// being updated (backend/apps/core/maintenance.py). api.js reports it here, and the app shows its "back soon"
// page until a page reload, or a sign-in by the team, finds Iga open again.
import { useSyncExternalStore } from "react";

let on = false;
const listeners = new Set();

export function setMaintenance(value) {
  if (on === Boolean(value)) return;
  on = Boolean(value);
  listeners.forEach((listener) => listener());
}

export function isMaintenance(data, status) {
  return status === 503 && data?.code === "maintenance";
}

function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useMaintenance() {
  return useSyncExternalStore(
    subscribe,
    () => on,
    () => false,
  );
}
