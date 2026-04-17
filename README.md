<p align="center">
  <img src="./confidant/public/images/confidant_text_purple.svg" alt="Confidant" width="400">
</p>

<p align="center">
  <strong>Your secret keeper.</strong><br>
  Open-source secret management service that stores secrets in DynamoDB, encrypted at rest with AWS KMS.
</p>

<p align="center">
  <a href="https://github.com/mappedsky/confidant/actions/workflows/ci.yml"><img src="https://github.com/mappedsky/confidant/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/mappedsky/confidant/blob/master/LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="License: Apache 2.0"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python 3.10+"></a>
</p>

---

Confidant is a secret management service built by Mapped Sky that provides secure, user-friendly storage and access to secrets. It uses AWS DynamoDB for persistent storage and AWS KMS for encryption at rest, ensuring your sensitive data is protected with industry-standard cryptography.

## Key Features

- **At-rest encryption** — Every secret revision gets a unique KMS data key, using Fernet symmetric authenticated cryptography
- **Versioned secret history** — Append-only storage with full audit trail, revision browsing, and rollback support
- **Service and group mappings** — Map secrets to services using user-defined group identifiers with conflict prevention
- **Modern web interface** — React + TypeScript UI built with Material UI for managing secrets, mappings, and history
- **RESTful API** — Full programmatic access to all secret management operations
- **Flexible authentication** — JWT/OIDC, SAML, and KMS authentication support
- **Fine-grained access control** — Pluggable ACL framework with role-based access control
- **Docker ready** — Production-ready container images published to GitHub Container Registry

## Quick Start

Pull and run the latest Docker image:

```bash
docker pull ghcr.io/mappedsky/confidant:master
docker run --rm ghcr.io/mappedsky/confidant:master --help
```

For a full local development environment with DynamoDB Local and mock KMS:

```bash
git clone https://github.com/mappedsky/confidant.git
cd confidant
make up
```

Confidant will be available at `http://localhost` (username: `confidant`, password: `confidant`).

## Documentation

Full documentation is available at **[mappedsky.github.io/confidant](https://mappedsky.github.io/confidant/)**.

- [Installation](https://mappedsky.github.io/confidant/install.html)
- [Configuration](https://mappedsky.github.io/confidant/configuration.html)
- [Usage Guide](https://mappedsky.github.io/confidant/using_confidant.html)
- [Contributing](https://mappedsky.github.io/confidant/contributing.html)

## Development

See the [development guide](https://mappedsky.github.io/confidant/contributing.html#development-guide) for full details. Quick summary:

```bash
make up                    # Start local dev environment
make docker_test           # Run full test suite
make docker_test_unit      # Run unit tests only
make docker_test_frontend  # Run frontend tests only
```

## Security

If you discover a security vulnerability, please report it through [GitHub Security Advisories](https://github.com/mappedsky/confidant/security/advisories). We will acknowledge your report and work to address it promptly.

## License

Confidant is licensed under the [Apache License 2.0](LICENSE).
