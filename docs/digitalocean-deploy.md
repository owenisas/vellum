# DigitalOcean Deployment

Vellum deploys to DigitalOcean App Platform as a containerized app:

- FastAPI backend served under `/api`
- Vite/React frontend built into the image and served by FastAPI under `/`

The GitHub Actions workflow at `.github/workflows/deploy-digitalocean.yml` builds
and pushes an image to DigitalOcean Container Registry, renders `.do/app.yaml.template`,
and deploys it with `doctl`.

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
DIGITALOCEAN_REGISTRY_NAME
DEMO_MODE=live
CHAIN_BACKEND=simulated
DEFAULT_PROVIDER=google
DEFAULT_MODEL=gemma-4-31b-it
AUTH0_DOMAIN=
AUTH0_AUDIENCE=https://api.vellum.io
AUTH0_SPA_CLIENT_ID=
```

If `DIGITALOCEAN_APP_ID` is omitted, a manual workflow run can create a new App
Platform app. After the first creation, save the app ID as `DIGITALOCEAN_APP_ID`
so future runs update the same app.
