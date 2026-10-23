import { api, ApiError } from "../api";

/**
 * Ask the server to build a teaching pack for one unit of a class.
 * Resolves {pack} when it was made, or {teaser} when the school hasn't subscribed (the server then says what a
 * pack would have found). Any other error is thrown. Building can take a while when Santa adds its suggestions.
 */
export async function createPack({ classroom, unit, lesson }) {
  try {
    const pack = await api("/teaching/packs/", { method: "POST", body: { classroom, unit, ...(lesson ? { lesson } : {}) } });
    return { pack };
  } catch (error) {
    if (error instanceof ApiError && error.status === 403 && error.data?.code === "subscription_required") {
      return { teaser: error.data.teaser ?? null };
    }
    throw error;
  }
}
