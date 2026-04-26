import { ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";

import { useAuth } from "../auth/useAuth";

export function AppShell({ children }: { children: ReactNode }) {
  const { isAuthenticated, login, logout, user } = useAuth();
  return (
    <>
      <nav className="nav">
        <Link to="/"><strong>Veritext</strong></Link>
        <NavLink to="/demo" className="nav-cta">Live Demo</NavLink>
        <NavLink to="/generate">Generate</NavLink>
        <NavLink to="/verify">Verify</NavLink>
        <NavLink to="/companies">Companies</NavLink>
        <NavLink to="/chain">Chain</NavLink>
        <NavLink to="/dashboard">Status</NavLink>
        <NavLink to="/about">About</NavLink>
        <span style={{ flex: 1 }} />
        {isAuthenticated ? (
          <>
            <span style={{ color: "var(--color-muted)" }}>{user?.email}</span>
            <button onClick={() => logout()}>Logout</button>
          </>
        ) : null /* hide login button entirely in demo mode */}
      </nav>
      <div className="shell">{children}</div>
    </>
  );
}
