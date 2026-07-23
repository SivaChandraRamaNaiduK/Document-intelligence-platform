/**
 * Global auth state. Wraps the app; any component can call useAuth()
 * to get the current user, loading state, and login/logout/register functions.
 *
 * On mount, if tokens exist in localStorage (from a previous session),
 * it tries to fetch the current user to restore the session automatically.
 */
import { createContext, useContext, useEffect, useState } from "react";
import * as authApi from "../api/auth";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function restoreSession() {
      const hasToken = localStorage.getItem("access_token");
      if (!hasToken) {
        setIsLoading(false);
        return;
      }
      try {
        const currentUser = await authApi.getCurrentUser();
        setUser(currentUser);
      } catch {
        // Token invalid/expired and refresh failed — client.js interceptor
        // will have already cleared tokens and redirected if needed.
      } finally {
        setIsLoading(false);
      }
    }
    restoreSession();
  }, []);

  async function login(email, password) {
    await authApi.login(email, password);
    const currentUser = await authApi.getCurrentUser();
    setUser(currentUser);
  }

  async function register(email, password) {
    await authApi.register(email, password);
    // Registration doesn't log the user in automatically — they log in next.
  }

  function logout() {
    authApi.logout();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}