import { lazy } from "react";

const loaders = {
  projectile: () => import("./Projectile"),
  grapher: () => import("./Grapher"),
  ohms: () => import("./OhmsLaw"),
  market: () => import("./Market"),
};

// provider_id → component, for simulations whose provider is "builtin".
export const BUILTIN_SIMS = Object.fromEntries(Object.entries(loaders).map(([key, load]) => [key, lazy(load)]));

/** Download every built-in lab's code (used by "Save for offline"; they are small). */
export function preloadBuiltinSims() {
  return Promise.all(Object.values(loaders).map((load) => load()));
}
