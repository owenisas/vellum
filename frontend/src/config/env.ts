/**
 * Typed environment access. All VITE_* vars are read at build-time.
 */

const env = {
  AUTH0_DOMAIN: (import.meta.env.VITE_AUTH0_DOMAIN ?? "").trim(),
  AUTH0_CLIENT_ID: (import.meta.env.VITE_AUTH0_CLIENT_ID ?? "").trim(),
  AUTH0_AUDIENCE:
    (import.meta.env.VITE_AUTH0_AUDIENCE ?? "https://api.vellum.io").trim(),
  API_BASE_URL:
    (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:5050").trim(),
};

export const features = {
  auth0: Boolean(env.AUTH0_DOMAIN && env.AUTH0_CLIENT_ID),
};

export default env;
