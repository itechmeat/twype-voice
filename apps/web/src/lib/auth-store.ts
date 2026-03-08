import { createContext } from "react";

export type AuthContextValue = {
  isAuthenticated: boolean;
  logout: () => void;
};

export const AuthContext = createContext<AuthContextValue | null>(null);
