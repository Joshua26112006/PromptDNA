"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  clearToken,
  getToken,
  login as apiLogin,
  me as apiMe,
  register as apiRegister,
  setToken,
  type User,
} from "./api";

interface AuthState {
  user: User | null;
  loading: boolean;
  register: (name: string, email: string, password: string) => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // On mount: if a token is present, try to resolve the current user.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const token = getToken();
      try {
        if (token) {
          const resolved = await apiMe(token);
          if (!cancelled) setUser(resolved);
        }
      } catch {
        clearToken();
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const token = await apiLogin(email, password);
    setToken(token);
    setUser(await apiMe(token));
  }, []);

  const register = useCallback(
    async (name: string, email: string, password: string) => {
      await apiRegister(name, email, password);
      // Convenience: log in immediately after registering.
      const token = await apiLogin(email, password);
      setToken(token);
      setUser(await apiMe(token));
    },
    [],
  );

  const logout = useCallback(() => {
    // Stateless JWT: logout is purely client-side — drop the token.
    clearToken();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, register, logout }),
    [user, loading, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}
