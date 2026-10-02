import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { api, refreshSession, setAccessToken, setSessionExpiredHandler } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  const startSession = useCallback((data) => {
    setAccessToken(data.access);
    setUser(data.user);
    return data.user;
  }, []);

  useEffect(() => {
    setSessionExpiredHandler(() => {
      setAccessToken(null);
      setUser(null);
    });
    refreshSession()
      .then((data) => setUser(data.user))
      .catch(() => setUser(null))
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
  }, []);

  const reloadUser = useCallback(async () => {
    const me = await api("/auth/me/");
    setUser(me);
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
