import { lazy } from "react";

// provider_id → component, for simulations whose provider is "builtin".
export const BUILTIN_SIMS = {
  projectile: lazy(() => import("./Projectile")),
  grapher: lazy(() => import("./Grapher")),
  ohms: lazy(() => import("./OhmsLaw")),
  market: lazy(() => import("./Market")),
};
