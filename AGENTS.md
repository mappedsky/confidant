# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What Confidant Is

A secret management system that stores credentials (key/value pairs) in DynamoDB, encrypted at rest via AWS KMS. Services (identified by IAM role ARN) are mapped to credentials; when a service authenticates, it receives only its mapped credentials. The web UI (React) and REST API (`/v1/*`) let operators manage credentials and service mappings.

## Commands

### Backend (Python)
```bash
docker compose exec confidant pipenv install               # install dependencies
docker compose exec confidant make test_unit               # run unit tests
docker compose exec confidant make test_integration        # run integration tests (requires DynamoDB + KMS locally)
docker compose exec confidant pipenv run pytest tests/unit/confidant/routes/credentials_test.py -v   # single test file
docker compose exec confidant pipenv run pytest tests/unit/confidant/routes/credentials_test.py::test_name -v  # single test
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
docker compose up    # starts: app (port 80), frontend (port 3000), dynamodb-local, kms-local, saml-idp
docker compose down
```

Use `localhost:3000` (the Vite dev server) during development, not port 80. The SAML auth flow is configured to round-trip through port 3000.
Prefer running Bun and Pipenv commands through `docker compose`; avoid host-installed toolchains so the local environment matches the containers used for builds and tests.

## Architecture

### Backend
- **Flask app** (`confidant/app.py`) with blueprints registered from `confidant/routes/`
- **Auth** (`confidant/authnz/`): pluggable via `USER_AUTH_MODULE` setting — supports SAML, Google OAuth, header-based, or null. The `@authnz.require_auth` decorator gates all API routes. CSRF is validated via `X-XSRF-TOKEN` header (token read from cookie whose name is returned by `/v1/client_config`).
- **Models** (`confidant/models/`): PynamoDB (DynamoDB ORM). `Credential` stores `credential_pairs` as KMS-encrypted blobs. `Service` stores a list of credential IDs.
- **Services layer** (`confidant/services/`): business logic; `credentialmanager` and `servicemanager` handle ACL checks and call `keymanager`/`ciphermanager` for encryption.
- **Schemas** (`confidant/schema/`): Pydantic v2 models for API response serialization. `CredentialResponse` has both `credential_keys` (always populated — the key names) and `credential_pairs` (only populated when `metadata_only=False` — the decrypted values). Service responses expose credential IDs only; credential payloads are returned from the credential endpoints after ACL and mapped-service authorization checks.
- **Settings** (`confidant/settings.py`): all configuration via environment variables.

### Frontend
- **Stack**: React 18, React Router v6, MUI v6, MUI X DataGrid v7, Vite, Bun.
- **Entry**: `confidant/public/src/App.tsx` — sets up MUI theme (system dark/light mode detection), `AppProvider`, and routes.
- **Theme**: `src/theme.ts` — `createAppTheme(mode)` factory. `primary.main` is intentionally dark (used for AppBar background). Form controls (Checkbox, TextField, Select, etc.) default to `color="secondary"` via theme `defaultProps` so focus/checked indicators use the high-contrast accent colour instead.
- **API client**: `src/api.ts` — wraps `fetch`; 401 responses redirect to `/v1/login`; reads XSRF cookie name from `AppContext` (set after `/v1/client_config` loads).
- **Global state** (`src/contexts/AppContext.tsx`): loads `clientConfig` (permissions, defined tags, aws_accounts, xsrf_cookie_name) and `userEmail` once on mount.
- **Credential detail flow**: on initial load, `getCredential(id, metadata_only=true)` returns `credential_keys` (names only) but not values. `populateForm` uses `credential_keys` to build rows with empty values for masked display. Clicking "show values" or "edit" triggers a second fetch with `metadata_only=false` to decrypt. Services no longer hydrate credentials in service detail responses.
- **View vs edit rendering**: detail pages use a local `ReadOnlyField` component (label + Typography) for view mode, and `TextField`/`Select` for edit mode. Never use `InputProps={{ readOnly }}` on TextField for display — it looks editable.
- **Vite proxy**: `/v1/*`, `/healthcheck`, `/loggedout`, `/custom` proxy to `http://confidant:80`. A `proxyRes` hook rewrites bare `http://localhost/` redirects to `localhost:3000` to keep the SAML round-trip on the dev server.

### Key data flow: credential decryption
```
GET /v1/credentials/{id}?metadata_only=false
  → route checks ACL (action='get')
  → CredentialResponse.from_credential(..., include_credential_pairs=True)
  → credential.decrypted_credential_pairs  (KMS decrypt)
  → JSON response with credential_pairs populated
```

## Testing notes
- `pytest.ini` sets env vars (fake KMS key, DynamoDB table names, session secret, `DYNAMODB_CREATE_TABLE=False`) so unit tests don't need running infrastructure.
- Integration tests require the services in `docker-compose.integration.yml`.
- Backend line length limit is 80 chars (`setup.cfg`).
