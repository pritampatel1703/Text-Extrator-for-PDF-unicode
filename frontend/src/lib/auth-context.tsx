"use client";

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { api, type TokenResponse, type UserResponse, type RegisterData } from "@/lib/api";

interface AuthState {
  user: UserResponse | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

interface AuthContextType extends AuthState {
  login: (username: string, password: string) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = "pdf_platform_token";
const USER_KEY = "pdf_platform_user";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    token: null,
    isAuthenticated: false,
    isLoading: true,
  });

  // Restore session from localStorage on mount
  useEffect(() => {
    try {
      const savedToken = localStorage.getItem(TOKEN_KEY);
      const savedUser = localStorage.getItem(USER_KEY);

      if (savedToken && savedUser) {
        const user = JSON.parse(savedUser) as UserResponse;
        api.setToken(savedToken);
        setState({
          user,
          token: savedToken,
          isAuthenticated: true,
          isLoading: false,
        });
      } else {
        setState((prev) => ({ ...prev, isLoading: false }));
      }
    } catch {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      setState((prev) => ({ ...prev, isLoading: false }));
    }
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const tokenRes: TokenResponse = await api.login(username, password);
    api.setToken(tokenRes.access_token);

    // We don't have a /me endpoint, so store minimal user info from the token
    // For now, create a synthetic user object from the login response
    const user: UserResponse = {
      id: "",
      email: username.includes("@") ? username : "",
      username,
      full_name: null,
      role: "user",
      is_active: true,
      created_at: new Date().toISOString(),
    };

    localStorage.setItem(TOKEN_KEY, tokenRes.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));

    setState({
      user,
      token: tokenRes.access_token,
      isAuthenticated: true,
      isLoading: false,
    });
  }, []);

  const register = useCallback(async (data: RegisterData) => {
    const user = await api.register(data);

    // Auto-login after registration
    const tokenRes = await api.login(data.username, data.password);
    api.setToken(tokenRes.access_token);

    localStorage.setItem(TOKEN_KEY, tokenRes.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));

    setState({
      user,
      token: tokenRes.access_token,
      isAuthenticated: true,
      isLoading: false,
    });
  }, []);

  const logout = useCallback(() => {
    api.setToken(null);
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setState({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
    });
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, register, logout }}>
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
