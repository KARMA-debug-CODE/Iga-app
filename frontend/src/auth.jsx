import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

import { api, ApiError, refreshSession, setAccessToken, setSessionExpiredHandler } from "./api";
import { clearAskHistory, clearOfflineData, forgetPremiumLessons } from "./offline";

const AuthContext = createContext(null);
const USER_KEY = "iga.user";

// A copy of the profile lets the app open without a connection (offline mode).
function rememberUser(user) {
  try {
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
    else localStorage.removeItem(USER_KEY);
  } catch {
    /* storage blocked */
  }
}

function rememberedUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || "null");
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  const lastLoaded = useRef(0);

  const startSession = useCallback((data) => {
    setAccessToken(data.access);
    // Someone else used this device before: their saved pages must not be shown to this user.
    const previous = rememberedUser();
    if (previous && previous.id !== data.user.id) clearOfflineData().catch(() => {});
    setUser(data.user);
    rememberUser(data.user);
    lastLoaded.current = Date.now();
    return data.user;
  }, []);

  useEffect(() => {
    setSessionExpiredHandler(() => {
      setAccessToken(null);
      setUser(null);
      clearOfflineData();
    });
    refreshSession()
      .then((data) => {
        const previous = rememberedUser();
        if (previous && previous.id !== data.user.id) clearOfflineData().catch(() => {});
        setUser(data.user);
        rememberUser(data.user);
        lastLoaded.current = Date.now();
      })
      .catch((err) => {
        if (err instanceof ApiError && [401, 403].includes(err.status)) {
          // The server says this session is over (expired or revoked) without anyone pressing
          // Log out: don't leave that person's saved pages for whoever signs in next.
          if (rememberedUser()) clearOfflineData().catch(() => {});
          clearAskHistory(); // this tab's chats, even if another tab already logged out
          setUser(null);
          return;
        }
        // No network, the server is down or busy (5xx, 429), rather than "not logged in": open in
        // offline mode with the saved lessons.
        const saved = rememberedUser();
        setUser(saved ? { ...saved, offline: true } : null);
      })
      .finally(() => setReady(true));
  }, []);

  // Logging out (or someone else logging in) in another tab ends this tab's session too, so a shared
  // computer never keeps showing the previous student's pages or Santa chats.
  const userId = user?.id;
  useEffect(() => {
    if (!userId) return undefined;
    function onStorage(event) {
      if (event.key !== USER_KEY) return;
      let other = null;
      try {
        other = JSON.parse(event.newValue || "null");
      } catch {
        /* unreadable: treat as logged out */
      }
      if (other?.id === userId) return;
      setAccessToken(null);
      clearAskHistory();
      setUser(null);
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, [userId]);

  // Without the subscription, saved copies of premium lessons are deleted.
  const premium = Boolean(user?.access?.premium);
  const online = Boolean(user) && !user.offline;
  useEffect(() => {
    if (online && !premium) forgetPremiumLessons().catch(() => {});
  }, [online, premium]);

  const login = useCallback(
    async (identifier, password, otp) =>
      startSession(await api("/auth/login/", { method: "POST", body: { identifier, password, otp } })),
    [startSession],
  );

  const register = useCallback(
    async (form) => startSession(await api("/auth/register/", { method: "POST", body: form })),
    [startSession],
  );

  const logout = useCallback(async () => {
    await api("/auth/logout/", { method: "POST" }).catch(() => {});
    setAccessToken(null);
    setUser(null);
    // Shared school computers: don't leave this student's cached pages for the next one.
    await clearOfflineData().catch(() => {});
  }, []);

  // Ends every session of the account on every device (this one too). Errors are thrown, so the page
  // can say so instead of pretending the other devices were signed out.
  const logoutEverywhere = useCallback(async () => {
    await api("/auth/logout-all/", { method: "POST" });
    setAccessToken(null);
    setUser(null);
    await clearOfflineData().catch(() => {});
  }, []);

  const reloadUser = useCallback(async () => {
    const me = await api("/auth/me/");
    setUser(me);
    rememberUser(me);
    lastLoaded.current = Date.now();
    return me;
  }, []);

  // Access changes when someone else acts (the school approves the student, the Iga team verifies
  // the school, the school pays): pick that up when the user comes back to the app.
  useEffect(() => {
    if (!online) return undefined;
    const refresh = () => {
      if (document.visibilityState === "visible" && Date.now() - lastLoaded.current > 60_000) {
        lastLoaded.current = Date.now();
        reloadUser().catch(() => {});
      }
    };
    window.addEventListener("focus", refresh);
    document.addEventListener("visibilitychange", refresh);
    return () => {
      window.removeEventListener("focus", refresh);
      document.removeEventListener("visibilitychange", refresh);
    };
  }, [online, reloadUser]);

  const value = useMemo(
    () => ({
      user,
      ready,
      login,
      register,
      logout,
      logoutEverywhere,
      reloadUser,
      setUser,
      isTeacher: !!user && (user.role === "admin" || (user.role === "teacher" && user.teacher_approved)),
      isAdmin: user?.role === "admin",
    }),
    [user, ready, login, register, logout, logoutEverywhere, reloadUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
