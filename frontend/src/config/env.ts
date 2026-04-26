export const env = {
  AUTH0_DOMAIN: (import.meta.env.VITE_AUTH0_DOMAIN as string) || "",
  AUTH0_CLIENT_ID: (import.meta.env.VITE_AUTH0_CLIENT_ID as string) || "",
  AUTH0_AUDIENCE:
    (import.meta.env.VITE_AUTH0_AUDIENCE as string) || "https://api.veritext.io",
  API_BASE_URL:
    (import.meta.env.VITE_API_BASE_URL as string) || "http://localhost:5050",
};

export const auth0Enabled = (): boolean => !!env.AUTH0_DOMAIN;
