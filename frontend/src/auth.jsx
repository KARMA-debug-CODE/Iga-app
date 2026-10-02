import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { api, ApiError, refreshSession, setAccessToken, setSessionExpiredHandler } from "./api";
import { clearOfflineData } from "./offline";

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

  const startSession = useCallback((data) => {
    setAccessToken(data.access);
    setUser(data.user);
    rememberUser(data.user);
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
        setUser(data.user);
        rememberUser(data.user);
      })
      .catch((err) => {
        // No network (rather than "not logged in"): open in offline mode with saved lessons.
        const saved = !(err instanceof ApiError) ? rememberedUser() : null;
        setUser(saved ? { ...saved, offline: true } : null);
      })
      .finally(() => setReady(true));
  }, []);

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
    return me;
  }, []);

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
