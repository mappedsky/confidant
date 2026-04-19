# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What Confidant Is

A secret management system that stores secrets (key/value pairs) in DynamoDB, encrypted at rest via AWS KMS. Groups are mapped to secrets by a user-defined group ID; when a service authenticates, it receives only its mapped secrets. The web UI (React) and REST API (`/v1/*`) let operators manage secrets and group mappings.

## Commands

### Backend (Python)
```bash
docker compose exec confidant pipenv install               # install dependencies
docker compose exec confidant make test_unit               # run unit tests
docker compose exec confidant make test_integration        # run integration tests (requires DynamoDB + KMS locally)
docker compose exec confidant pipenv run pytest tests/unit/confidant/routes/secrets_test.py -v   # single test file
docker compose exec confidant pipenv run pytest tests/unit/confidant/routes/secrets_test.py::test_name -v  # single test
docker compose exec confidant pipenv run confidant-admin   # management CLI
```

### Frontend (Bun + Vite)
```bash
docker compose run --rm frontend bun install      # install dependencies
docker compose run --rm frontend bun run dev      # dev server on port 3000 (proxies /v1/* to backend)
docker compose run --rm frontend bun run build    # production build → confidant/dist/
```

### Local full-stack dev
```bash
docker compose up    # starts: app (port 80), frontend (port 3000), dynamodb-local, kms-local, authentik
docker compose down
```

Use `localhost:3000` (the Vite dev server) during development, not port 80. The OIDC callback is configured to round-trip through port 3000. Authentik runs at `http://localhost:9000` with dev secrets `akadmin/devpassword`, `confidant-administrator/devpassword`, `confidant-group-administrator/devpassword`, `confidant-auditor/devpassword`, and `dashboard-engineering/devpassword`.
Prefer running Bun and Pipenv commands through `docker compose`; avoid host-installed toolchains so the local environment matches the containers used for builds and tests.

## Architecture

### Backend
- **Flask app** (`confidant/app.py`) with blueprints registered from `confidant/routes/`
- **Auth** (`confidant/authnz/`): JWT-only. The backend validates Bearer tokens against `JWKS_URL`, derives `user` vs `service` from a JWT claim (`JWT_PRINCIPAL_TYPE_CLAIM`), and populates `flask.g` with a normalized request principal. Browser login is handled by the React app via OIDC PKCE against Authentik.
- **Storage layer** (`confidant/services/dynamodbstore.py`): single-table DynamoDB access. Secret and group records, versions, and archive partitions are all stored via explicit PK/SK patterns rather than ORM models.
- **Groups layer** (`confidant/groups/`): business logic; `secretmanager` and `groupmanager` handle ACL checks and call `keymanager`/`ciphermanager` for encryption.
- **Schemas** (`confidant/schema/`): Pydantic v2 models for API response serialization. `SecretResponse` has both `secret_keys` (always populated — the key names) and `secret_pairs` (only populated on explicit decrypt responses — the decrypted values). Group responses expose secret IDs only; secret payloads are returned from the secret endpoints after ACL and mapped-service authorization checks.
- **Settings** (`confidant/settings.py`): all configuration via environment variables.

### Frontend
- **Stack**: React 18, React Router v6, MUI v6, MUI X DataGrid v7, Vite, Bun.
- **Entry**: `confidant/public/src/App.tsx` — sets up MUI theme (system dark/light mode detection), `AppProvider`, and routes.
- **Theme**: `src/theme.ts` — `createAppTheme(mode)` factory. `primary.main` is intentionally dark (used for AppBar background). Form controls (Checkbox, TextField, Select, etc.) default to `color="secondary"` via theme `defaultProps` so focus/checked indicators use the high-contrast accent colour instead.
- **API client**: `src/api.ts` — wraps `fetch`; attaches a Bearer token supplied by the OIDC auth provider and redirects back into the OIDC flow on 401s.
- **Global state** (`src/contexts/AppContext.tsx`): loads `clientConfig` (permissions, defined tags) and `userEmail` once on mount.
- **Secret detail flow**: on initial load, `getSecret(id)` returns `secret_keys` (names only) but not values. `populateForm` uses `secret_keys` to build rows with empty values for masked display. Clicking "show values" or "edit" triggers an explicit `POST /v1/secrets/{id}/decrypt` call; version pages use `POST /v1/secrets/{id}/versions/{version}/decrypt`. Groups no longer hydrate secrets in group detail responses.
- **View vs edit rendering**: detail pages use a local `ReadOnlyField` component (label + Typography) for view mode, and `TextField`/`Select` for edit mode. Never use `InputProps={{ readOnly }}` on TextField for display — it looks editable.
- **Vite proxy**: `/v1/*`, `/healthcheck`, `/loggedout`, `/custom` proxy to `http://confidant:80`. A `proxyRes` hook rewrites bare `http://localhost/` redirects to `localhost:3000` so OIDC/logout redirects return to the Vite dev server cleanly.

### Key data flow: secret decryption
```
POST /v1/secrets/{id}/decrypt
  → route checks ACL (action='decrypt')
  → SecretResponse.from_secret(..., include_secret_pairs=True)
  → secret.decrypted_secret_pairs  (KMS decrypt)
  → JSON response with secret_pairs populated

POST /v1/secrets/{id}/versions/{version}/decrypt
  → route checks ACL (action='decrypt')
  → SecretResponse.from_secret(..., include_secret_pairs=True)
  → secret.decrypted_secret_pairs  (KMS decrypt)
  → JSON response with secret_pairs populated
```

## Testing notes
- `pytest.ini` sets env vars (fake KMS key, DynamoDB table names, `DYNAMODB_CREATE_TABLE=False`) so unit tests don't need running infrastructure.
- Integration tests require the groups in `docker-compose.integration.yml`.
- Backend line length limit is 80 chars (`setup.cfg`).
