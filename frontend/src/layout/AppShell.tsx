import { ReactNode } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/useAuth";

export function AppShell({ children }: { children: ReactNode }) {
  const { isAuthenticated, login, logout, user } = useAuth();
  return (
    <>
      <nav className="nav">
        <Link to="/"><strong>Veritext</strong></Link>
        <Link to="/dashboard">Dashboard</Link>
        <Link to="/generate">Generate</Link>
        <Link to="/verify">Verify</Link>
        <Link to="/companies">Companies</Link>
        <Link to="/chain">Chain</Link>
        <Link to="/about">About</Link>
        <span style={{ flex: 1 }} />
        {isAuthenticated ? (
          <>
            <span style={{ color: "var(--color-muted)" }}>{user?.email}</span>
            <button onClick={() => logout()}>Logout</button>
          </>
        ) : (
          <button onClick={() => login()}>Login</button>
        )}
      </nav>
      <div className="shell">{children}</div>
    </>
  );
}
