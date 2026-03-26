"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { getMe, login as apiLogin, register as apiRegister } from "@/lib/api";

type User = {
  id: number;
  username: string;
  email: string;
  role: "MANAGER" | "EMPLOYEE";
};

type AuthContextType = {
  user: User | null;
  loading: boolean;
  login: (payload: any) => Promise<void>;
  register: (payload: any) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem("token");
      if (token) {
        try {
          const userData = await getMe();
          setUser(userData);
        } catch (err) {
          localStorage.removeItem("token");
        }
      }
      setLoading(false);
    };
    initAuth();
  }, []);

  const login = async (payload: any) => {
    const data = await apiLogin(payload);
    localStorage.setItem("token", data.access_token);
    const userData = await getMe();
    setUser(userData);
  };

  const register = async (payload: any) => {
    await apiRegister(payload);
    await login({ username: payload.username, password: payload.password });
  };

  const logout = () => {
    localStorage.removeItem("token");
    setUser(null);
    window.location.href = "/";
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
