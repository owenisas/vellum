#!/usr/bin/env bash
# Auth0 tenant provisioning (interactive). Manual fallback documented in docs/architecture.md.
set -euo pipefail

echo "Auth0 setup is interactive. You'll need:"
echo "  - An Auth0 tenant (free tier OK)"
echo "  - A Management API token (Dashboard → APIs → Auth0 Management API → API Explorer)"
echo
read -rp "Auth0 domain (e.g. veritext.us.auth0.com): " DOMAIN
read -rp "Management API token: " TOKEN

API_ID="https://api.veritext.io"

echo "==> Creating API resource server: $API_ID"
curl -fsS -X POST "https://$DOMAIN/api/v2/resource-servers" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"name\": \"Veritext API\",
        \"identifier\": \"$API_ID\",
        \"signing_alg\": \"RS256\",
        \"scopes\": [
            {\"value\": \"anchor:create\", \"description\": \"Anchor responses\"},
            {\"value\": \"company:create\", \"description\": \"Register companies\"},
            {\"value\": \"company:rotate_key\", \"description\": \"Rotate company key\"},
            {\"value\": \"chat:invoke\", \"description\": \"Invoke chat\"},
            {\"value\": \"admin:reset\", \"description\": \"Admin reset\"}
        ]
    }" || echo "(may already exist; continuing)"

echo "==> Append to .env:"
echo "AUTH0_DOMAIN=$DOMAIN"
echo "AUTH0_AUDIENCE=$API_ID"
echo
echo "==> Append to frontend/.env:"
echo "VITE_AUTH0_DOMAIN=$DOMAIN"
echo "VITE_AUTH0_AUDIENCE=$API_ID"
