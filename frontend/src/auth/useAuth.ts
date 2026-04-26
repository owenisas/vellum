import { useAuth0 } from "@auth0/auth0-react";
import { features } from "../config/env";

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: { sub?: string; email?: string; name?: string } | null;
  login: () => void;
  logout: () => void;
  demo: boolean;
}

const DEMO_STATE: AuthState = {
  isAuthenticated: true,
  isLoading: false,
  user: { sub: "demo|anonymous", email: "demo@vellum.local", name: "Demo User" },
  login: () => {
    /* noop */
  },
  logout: () => {
    /* noop */
  },
  demo: true,
};

/** Unified auth hook. Returns a demo identity when Auth0 is disabled. */
export function useAuth(): AuthState {
  if (!features.auth0) return DEMO_STATE;
  return useAuthLive();
}

function useAuthLive(): AuthState {
  const auth = useAuth0();
  return {
    isAuthenticated: auth.isAuthenticated,
    isLoading: auth.isLoading,
    user: auth.user
      ? { sub: auth.user.sub, email: auth.user.email, name: auth.user.name }
      : null,
    login: () => auth.loginWithRedirect(),
    logout: () =>
      auth.logout({ logoutParams: { returnTo: window.location.origin } }),
    demo: false,
  };
}
