import type { ReactNode } from "react";
import { useAuth } from "./useAuth";
import { features } from "../config/env";

export function AuthGuard({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading, login } = useAuth();

  if (!features.auth0) return <>{children}</>;
  if (isLoading) {
    return (
      <div className="card">
        <p>Checking authentication…</p>
      </div>
    );
  }
  if (!isAuthenticated) {
    return (
      <div className="card">
        <h2>Login required</h2>
        <p>Sign in to access this page.</p>
        <button className="btn" onClick={login}>
          Log in with Auth0
        </button>
      </div>
    );
  }
  return <>{children}</>;
}
