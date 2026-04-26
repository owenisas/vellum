import { NavLink, Outlet } from "react-router";
import { useAuth } from "../auth/useAuth";
import { Button } from "../components/ui";

export function AppShell() {
  const { isAuthenticated, login, logout, user, demo } = useAuth();

  return (
    <div className="app-shell">
      <nav className="nav">
        <NavLink to="/" className="nav-brand">
          Vellum
        </NavLink>
        <div className="nav-links">
          <NavLink
            to="/dashboard"
            className={({ isActive }) =>
              isActive ? "nav-link active" : "nav-link"
            }
          >
            Dashboard
          </NavLink>
          <NavLink
            to="/generate"
            className={({ isActive }) =>
              isActive ? "nav-link active" : "nav-link"
            }
          >
            Generate
          </NavLink>
          <NavLink
            to="/verify"
            className={({ isActive }) =>
              isActive ? "nav-link active" : "nav-link"
            }
          >
            Verify
          </NavLink>
          <NavLink
            to="/chain"
            className={({ isActive }) =>
              isActive ? "nav-link active" : "nav-link"
            }
          >
            Chain
          </NavLink>
          <NavLink
            to="/companies"
            className={({ isActive }) =>
              isActive ? "nav-link active" : "nav-link"
            }
          >
            Companies
          </NavLink>
          <NavLink
            to="/demo"
            className={({ isActive }) =>
              isActive ? "nav-link active" : "nav-link"
            }
          >
            Guided Demo
          </NavLink>
        </div>
        <div className="flex gap-sm">
          {demo ? (
            <span className="muted" style={{ fontSize: "0.85rem" }}>
              demo mode
            </span>
          ) : isAuthenticated ? (
            <>
              <span className="muted" style={{ fontSize: "0.85rem" }}>
                {user?.email ?? user?.sub}
              </span>
              <Button variant="secondary" onClick={logout}>
                Sign out
              </Button>
            </>
          ) : (
            <Button onClick={login}>Sign in</Button>
          )}
        </div>
      </nav>
      <Outlet />
    </div>
  );
}
