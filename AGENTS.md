# Confidant

Confidant is a secret management system and client that stores secrets in DynamoDB, encrypted at rest using AWS KMS. It provides a REST API and a user-friendly AngularJS-based web interface for managing secrets and certificates.

## Project Overview

-   **Backend:** Python 3.10 with Flask 3.x. Uses `pipenv` for dependency management.
-   **Database:** Amazon DynamoDB (via `pynamodb`).
-   **Encryption:** AWS KMS (via `boto3`).
-   **Frontend:** Legacy AngularJS application, built using Vite and Bun.
-   **Infrastructure:** Multi-stage Docker build for both frontend and backend.

## Building and Running

### Prerequisites
- Docker and Docker Compose
- Python 3.10+ and Pipenv
- Bun (for frontend development)

### Commands

| Task | Command |
| :--- | :--- |
| **Install Dependencies** | `pipenv install` (backend), `bun install` (frontend) |
| **Build Project** | `make docker_build` or `docker build -t lyft/confidant .` |
| **Run Locally** | `docker-compose up` |
| **Run Unit Tests** | `make test_unit` (runs via pipenv) |
| **Run Integration Tests** | `make test_integration` (requires DynamoDB/KMS local) |
| **Build Frontend** | `make test_frontend` (runs Vite build via Docker/Bun) |
| **Admin CLI** | `pipenv run confidant-admin` (uses Click-based CLI) |

## Development Conventions

-   **Backend Style:** Follows PEP8 with a maximum line length of 80 (configured in `setup.cfg`).
-   **Type Checking:** Uses `mypy` for static type checking.
-   **CLI:** All management scripts are implemented using `click` in `confidant/scripts/`.
-   **Frontend Assets:** Built assets are served from `confidant/dist/`. Development happens in `confidant/public/`.
-   **Testing:** New features or bug fixes should include tests in `tests/unit/` or `tests/integration/`.

## Key Directories

-   `confidant/`: Main application source code.
    -   `authnz/`: Authentication and authorization logic.
    -   `models/`: PynamoDB models for credentials, services, etc.
    -   `public/`: Frontend source (AngularJS, styles, images).
    -   `routes/`: Flask blueprints for API endpoints.
    -   `scripts/`: Management and migration CLI scripts.
    -   `services/`: Business logic for key management, certificates, etc.
-   `tests/`: Unit and integration tests.
-   `config/`: Configuration files for development and production.
-   `docs/`: Project documentation.
