import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

const STORAGE_KEY = "prism-auth";

export type Credentials = {
  username: string;
  password: string;
};

export type AuthContextValue = {
  credentials: Credentials | null;
  authorization: string | null;
  login: (creds: Credentials) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const loadStoredCredentials = (): Credentials | null => {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw);
    if (parsed?.username && parsed?.password) {
      return parsed as Credentials;
    }
    return null;
  } catch {
    return null;
  }
};

const encodeBasic = (creds: Credentials | null): string | null => {
  if (!creds) {
    return null;
  }
  try {
    return `Basic ${btoa(`${creds.username}:${creds.password}`)}`;
  } catch {
    return null;
  }
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [credentials, setCredentials] = useState<Credentials | null>(loadStoredCredentials);

  const value = useMemo<AuthContextValue>(() => {
    const authorization = encodeBasic(credentials);
    const login = (creds: Credentials) => {
      setCredentials(creds);
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(creds));
    };
    const logout = () => {
      setCredentials(null);
      sessionStorage.removeItem(STORAGE_KEY);
    };

    return { credentials, authorization, login, logout };
  }, [credentials]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
