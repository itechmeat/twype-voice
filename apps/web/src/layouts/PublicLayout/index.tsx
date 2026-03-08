import { Navigate, Outlet } from "react-router";
import { useAuth } from "../../lib/use-auth";

export function PublicLayout() {
  const { isAuthenticated } = useAuth();

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
