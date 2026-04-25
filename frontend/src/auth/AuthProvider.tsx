import { Auth0Provider } from "@auth0/auth0-react";
import { features } from "../config/env";
import env from "../config/env";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  if (!features.auth0) {
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
          "openid profile email anchor:create company:create chat:invoke",
      }}
      cacheLocation="localstorage"
      useRefreshTokens
    >
      {children}
    </Auth0Provider>
  );
}
