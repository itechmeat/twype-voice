import { NavLink, Navigate, Outlet } from "react-router";
import { useAuth } from "../lib/use-auth";

export function ProtectedLayout() {
  const { isAuthenticated, logout } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="app-shell">
      <header className="app-shell__header">
        <div className="app-shell__header-copy">
          <p className="eyebrow">Twype</p>
          <h1>Conversation workspace</h1>
        </div>
        <div className="app-shell__header-actions">
          <nav aria-label="Primary" className="app-shell__nav">
            <NavLink
              className={({ isActive }) =>
                isActive ? "app-shell__nav-link app-shell__nav-link--active" : "app-shell__nav-link"
              }
              end
              to="/"
            >
              Chat
            </NavLink>
            <NavLink
              className={({ isActive }) =>
                isActive ? "app-shell__nav-link app-shell__nav-link--active" : "app-shell__nav-link"
              }
              to="/history"
            >
              History
            </NavLink>
          </nav>
          <button className="app-shell__logout" onClick={logout} type="button">
            Logout
          </button>
        </div>
      </header>
      <main className="app-shell__content">
        <Outlet />
      </main>
    </div>
  );
}
