import { useAuth0 } from "@auth0/auth0-react";

import { auth0Enabled } from "../config/env";

export function useAuth() {
  if (!auth0Enabled()) {
    return {
      isAuthenticated: true,
      isLoading: false,
      user: { sub: "demo|local", email: "demo@veritext.local" },
      login: async () => {},
      logout: () => {},
      getToken: async () => null,
    };
  }
  const { isAuthenticated, isLoading, user, loginWithRedirect, logout, getAccessTokenSilently } = useAuth0();
  return {
    isAuthenticated,
    isLoading,
    user,
    login: () => loginWithRedirect(),
    logout: () => logout({ logoutParams: { returnTo: window.location.origin } }),
    getToken: async () => {
      try {
        return await getAccessTokenSilently();
      } catch {
        return null;
      }
    },
  };
}
