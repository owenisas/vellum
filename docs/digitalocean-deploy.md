# DigitalOcean Deployment

Vellum deploys to DigitalOcean App Platform as two components:

- `api`: FastAPI backend served under `/api`
- `web`: Vite/React static frontend served under `/`

The GitHub Actions workflow at `.github/workflows/deploy-digitalocean.yml` renders
`.do/app.yaml.template` and deploys it with `doctl`.

## Required GitHub Secret

Set this repository secret before running the workflow:

```text
DIGITALOCEAN_ACCESS_TOKEN
```

Do not commit DigitalOcean tokens or paste them into config files.

## Recommended GitHub Secrets

```text
REGISTRY_ADMIN_SECRET
GOOGLE_API_KEY
MINIMAX_API_KEY
```

## Recommended GitHub Variables

```text
DIGITALOCEAN_APP_ID
DEMO_MODE=live
CHAIN_BACKEND=simulated
DEFAULT_PROVIDER=google
DEFAULT_MODEL=gemma-4-27b-it
AUTH0_DOMAIN=
AUTH0_AUDIENCE=https://api.vellum.io
AUTH0_SPA_CLIENT_ID=
```

If `DIGITALOCEAN_APP_ID` is omitted, a manual workflow run can create a new App
Platform app. After the first creation, save the app ID as `DIGITALOCEAN_APP_ID`
so future runs update the same app.
