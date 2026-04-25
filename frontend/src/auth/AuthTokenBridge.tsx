import { useAuth0 } from "@auth0/auth0-react";
import { useEffect } from "react";
import { setTokenGetter } from "../api/client";
import { features } from "../config/env";

/** Bridges the Auth0 access token into the api client. */
export function AuthTokenBridge() {
  if (!features.auth0) return null;
  return <BridgeInner />;
}

function BridgeInner() {
  const { getAccessTokenSilently, isAuthenticated } = useAuth0();

  useEffect(() => {
    if (isAuthenticated) {
      setTokenGetter(() => getAccessTokenSilently());
    } else {
      setTokenGetter(null);
    }
  }, [isAuthenticated, getAccessTokenSilently]);

  return null;
}
