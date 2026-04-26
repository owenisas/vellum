#!/usr/bin/env bash
# Auth0 tenant provisioning for Vellum.
# Creates: API resource server, SPA app, M2M app, and a client_grant.
set -euo pipefail

RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
BLUE=$'\033[0;34m'
CYAN=$'\033[0;36m'
BOLD=$'\033[1m'
RESET=$'\033[0m'

info()  { echo "${CYAN}==>${RESET} $*"; }
ok()    { echo "${GREEN}[ok]${RESET} $*"; }
warn()  { echo "${YELLOW}[warn]${RESET} $*"; }
fail()  { echo "${RED}[fail]${RESET} $*" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE=".env"
FRONTEND_ENV_FILE="frontend/.env"
AUDIENCE="https://api.vellum.io"

command -v curl >/dev/null 2>&1 || fail "curl is required."
command -v python3 >/dev/null 2>&1 || fail "python3 is required (used to parse JSON)."

echo "${BOLD}${BLUE}Vellum Auth0 setup${RESET}"
echo

# ----- Prompts -----
read -r -p "Auth0 domain (e.g. vellum.us.auth0.com): " AUTH0_DOMAIN
[ -n "${AUTH0_DOMAIN:-}" ] || fail "AUTH0_DOMAIN required."

echo "Need a Management API token with scopes:"
echo "  read:clients write:clients write:client_credentials read:resource_servers create:resource_servers"
read -r -s -p "Management API token: " MGMT_TOKEN
echo
[ -n "${MGMT_TOKEN:-}" ] || fail "Management token required."

API_BASE="https://${AUTH0_DOMAIN}/api/v2"
AUTH_HDR=(-H "Authorization: Bearer ${MGMT_TOKEN}" -H "Content-Type: application/json")

# ----- helpers -----
json_get() {
  # json_get <python-expr> reads stdin (parsed as JSON) and prints expr result.
  python3 -c "import json,sys; d=json.load(sys.stdin); print($1)"
}

curl_json() {
  # curl_json <method> <url> [json-body]
  local method="$1" url="$2" body="${3:-}"
  if [ -n "$body" ]; then
    curl -sS --fail-with-body -X "$method" "$url" "${AUTH_HDR[@]}" -d "$body"
  else
    curl -sS --fail-with-body -X "$method" "$url" "${AUTH_HDR[@]}"
  fi
}

patch_env() {
  local key="$1" val="$2" file="$3"
  [ -f "$file" ] || { mkdir -p "$(dirname "$file")"; touch "$file"; }
  cp "$file" "$file.bak.$$"
  if grep -qE "^${key}=" "$file"; then
    awk -v k="$key" -v v="$val" -F= 'BEGIN{OFS="="} { if ($1==k) print k,v; else print $0 }' "$file.bak.$$" > "$file"
  else
    cp "$file.bak.$$" "$file"
    printf '%s=%s\n' "$key" "$val" >> "$file"
  fi
  rm -f "$file.bak.$$"
}

# ----- Validate token -----
info "Validating Management API token"
if ! curl -sS --fail-with-body "${API_BASE}/clients?per_page=1" "${AUTH_HDR[@]}" >/dev/null; then
  fail "Token invalid or insufficient scope (GET /clients failed)."
fi
ok "token valid"

# ----- Resource server -----
info "Creating API resource server (${AUDIENCE})"
RS_BODY=$(cat <<JSON
{
  "name": "Vellum API",
  "identifier": "${AUDIENCE}",
  "signing_alg": "RS256",
  "scopes": [
    {"value": "anchor:create",  "description": "Create blockchain anchors"},
    {"value": "company:create", "description": "Register a company"},
    {"value": "chat:invoke",    "description": "Invoke chat / signing flows"},
    {"value": "admin:reset",    "description": "Administrative reset operations"}
  ]
}
JSON
)
RS_TMP="$(mktemp)"
RS_HTTP=$(curl -sS -o "$RS_TMP" -w "%{http_code}" -X POST "${API_BASE}/resource-servers" "${AUTH_HDR[@]}" -d "$RS_BODY" || true)
case "$RS_HTTP" in
  20*) ok "resource server created" ;;
  409) warn "resource server with identifier ${AUDIENCE} already exists; skipping" ;;
  *)
    echo "${RED}Resource-server creation failed (HTTP $RS_HTTP):${RESET}" >&2
    cat "$RS_TMP" >&2; echo >&2
    rm -f "$RS_TMP"
    fail "POST /resource-servers"
    ;;
esac
rm -f "$RS_TMP"

# ----- SPA client -----
info "Creating SPA application"
SPA_BODY=$(cat <<'JSON'
{
  "name": "Vellum SPA",
  "app_type": "spa",
  "callbacks": ["http://localhost:5173", "http://localhost:5050"],
  "allowed_logout_urls": ["http://localhost:5173", "http://localhost:5050"],
  "web_origins": ["http://localhost:5173", "http://localhost:5050"],
  "grant_types": ["authorization_code", "refresh_token", "implicit"],
  "token_endpoint_auth_method": "none"
}
JSON
)
if ! SPA_RESP="$(curl_json POST "${API_BASE}/clients" "$SPA_BODY")"; then
  echo "$SPA_RESP" >&2
  fail "POST /clients (SPA)"
fi
SPA_CLIENT_ID="$(printf '%s' "$SPA_RESP" | json_get "d['client_id']")"
ok "SPA client_id: $SPA_CLIENT_ID"

# ----- M2M client -----
info "Creating M2M application"
M2M_BODY=$(cat <<'JSON'
{
  "name": "Vellum M2M",
  "app_type": "non_interactive",
  "grant_types": ["client_credentials"]
}
JSON
)
if ! M2M_RESP="$(curl_json POST "${API_BASE}/clients" "$M2M_BODY")"; then
  echo "$M2M_RESP" >&2
  fail "POST /clients (M2M)"
fi
M2M_CLIENT_ID="$(printf '%s' "$M2M_RESP" | json_get "d['client_id']")"
M2M_CLIENT_SECRET="$(printf '%s' "$M2M_RESP" | json_get "d['client_secret']")"
ok "M2M client_id: $M2M_CLIENT_ID"

# ----- Client grant (authorize M2M -> API) -----
info "Authorizing M2M client against API"
GRANT_BODY=$(cat <<JSON
{
  "client_id": "${M2M_CLIENT_ID}",
  "audience": "${AUDIENCE}",
  "scope": ["anchor:create", "chat:invoke"]
}
JSON
)
if ! curl_json POST "${API_BASE}/client-grants" "$GRANT_BODY" >/dev/null; then
  fail "POST /client-grants"
fi
ok "client-grant created"

# ----- Patch env files -----
info "Patching $ENV_FILE"
patch_env "AUTH0_DOMAIN"        "$AUTH0_DOMAIN"   "$ENV_FILE"
patch_env "AUTH0_AUDIENCE"      "$AUDIENCE"       "$ENV_FILE"
patch_env "AUTH0_SPA_CLIENT_ID" "$SPA_CLIENT_ID"  "$ENV_FILE"
ok "backend .env updated"

info "Patching $FRONTEND_ENV_FILE"
patch_env "VITE_AUTH0_DOMAIN"    "$AUTH0_DOMAIN"  "$FRONTEND_ENV_FILE"
patch_env "VITE_AUTH0_CLIENT_ID" "$SPA_CLIENT_ID" "$FRONTEND_ENV_FILE"
patch_env "VITE_AUTH0_AUDIENCE"  "$AUDIENCE"      "$FRONTEND_ENV_FILE"
ok "frontend .env updated"

# ----- Summary -----
echo
echo "${GREEN}${BOLD}Auth0 setup complete.${RESET}"
echo
echo "${BOLD}Fetch an M2M token with:${RESET}"
cat <<EOF
  curl --request POST \\
    --url https://${AUTH0_DOMAIN}/oauth/token \\
    --header 'content-type: application/json' \\
    --data '{
      "client_id": "${M2M_CLIENT_ID}",
      "client_secret": "${M2M_CLIENT_SECRET}",
      "audience": "${AUDIENCE}",
      "grant_type": "client_credentials"
    }'
EOF
echo
echo "${YELLOW}Save the M2M client_secret somewhere safe; it is shown only once.${RESET}"
exit 0
