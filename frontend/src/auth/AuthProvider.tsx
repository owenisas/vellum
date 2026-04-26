import { Auth0Provider } from "@auth0/auth0-react";
import { ReactNode, useEffect } from "react";

import { setTokenGetter } from "../api/client";
import { auth0Enabled, env } from "../config/env";

import { AuthTokenBridge } from "./AuthTokenBridge";

export function AuthProvider({ children }: { children: ReactNode }) {
  useEffect(() => {
    if (!auth0Enabled()) {
      // Demo mode: no token
      setTokenGetter(async () => null);
    }
  }, []);

  if (!auth0Enabled()) {
    return <>{children}</>;
  }

  return (
    <Auth0Provider
      domain={env.AUTH0_DOMAIN}
      clientId={env.AUTH0_CLIENT_ID}
      authorizationParams={{
        redirect_uri: window.location.origin,
        audience: env.AUTH0_AUDIENCE,
        scope:
          "openid profile email anchor:create company:create company:rotate_key chat:invoke",
      }}
      cacheLocation="localstorage"
    >
      <AuthTokenBridge />
      {children}
    </Auth0Provider>
  );
}
