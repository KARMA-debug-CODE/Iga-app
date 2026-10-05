import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

import { api, ApiError, refreshSession, setAccessToken, setSessionExpiredHandler } from "./api";
import { clearOfflineData, forgetPremiumLessons } from "./offline";

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
      reloadUser,
      setUser,
      isTeacher: !!user && (user.role === "admin" || (user.role === "teacher" && user.teacher_approved)),
      isAdmin: user?.role === "admin",
    }),
    [user, ready, login, register, logout, reloadUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
