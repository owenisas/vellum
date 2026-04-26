import { useAuth0 } from "@auth0/auth0-react";
import { useEffect } from "react";

import { setTokenGetter } from "../api/client";

export function AuthTokenBridge() {
  const { isAuthenticated, getAccessTokenSilently } = useAuth0();
  useEffect(() => {
    if (isAuthenticated) {
      setTokenGetter(async () => {
        try {
          return await getAccessTokenSilently();
        } catch {
          return null;
        }
      });
    } else {
      setTokenGetter(async () => null);
    }
  }, [isAuthenticated, getAccessTokenSilently]);
  return null;
}
