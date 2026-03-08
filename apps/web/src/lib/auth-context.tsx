import { useEffect, useState, type ReactNode } from "react";
import { clearTokens, getTokens, subscribeToTokenChanges } from "./auth-tokens";
import { redirectToLogin } from "./navigation";
import { AuthContext, type AuthContextValue } from "./auth-store";

function readAuthenticationState(): boolean {
  return getTokens().accessToken !== null;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() => readAuthenticationState());

  useEffect(() => {
    setIsAuthenticated(readAuthenticationState());

    return subscribeToTokenChanges(() => {
      setIsAuthenticated(readAuthenticationState());
    });
  }, []);

  const contextValue: AuthContextValue = {
    isAuthenticated,
    // TODO(S22): Decode the access token and expose user identity once the app shell needs it.
    logout: () => {
      clearTokens();
      setIsAuthenticated(false);
      redirectToLogin();
    },
  };

  return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>;
}
