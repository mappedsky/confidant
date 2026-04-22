import logging
import os
import secrets as stdlib_secrets
from urllib.parse import urlparse

import boto3
from flask import Flask, g
from flask_sslify import SSLify

from confidant import settings
from confidant.routes import groups, identity, secrets, static_files
from confidant.utils.dynamodb import create_dynamodb_tables
from confidant.utils.logging import configure_logging, log_request, start_request_timer

if not settings.get("DEBUG"):
    boto3.set_stream_logger(level=logging.CRITICAL)
    logging.getLogger("botocore").setLevel(logging.CRITICAL)


def _build_csp_policy(nonce):
    policy = {
        "default-src": ["'self'"],
        "connect-src": ["'self'"],
        "style-src": ["'self'", f"'nonce-{nonce}'"],
    }
    if settings.OIDC_AUTHORITY:
        parsed = urlparse(settings.OIDC_AUTHORITY)
        oidc_origin = f"{parsed.scheme}://{parsed.netloc}"
        if oidc_origin not in policy["connect-src"]:
            policy["connect-src"].append(oidc_origin)
        policy["frame-src"] = [oidc_origin]
    return policy


def _format_csp_policy(policy):
    parts = []
    for directive, sources in policy.items():
        parts.append(f"{directive} {' '.join(sources)}")
    return "; ".join(parts)


def _resolve_static_folder(static_folder):
    candidates = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), static_folder)),
    ]
    if not static_folder.startswith("../"):
        candidates.append(
            os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", static_folder),
            ),
        )

    for candidate in candidates:
        if os.path.isfile(os.path.join(candidate, "index.html")):
            return candidate

    for candidate in candidates:
        if os.path.isdir(candidate):
            return candidate

    return candidates[0]


def create_app():
    static_folder = _resolve_static_folder(settings.STATIC_FOLDER)
    configure_logging(settings.LOG_LEVEL, settings.AUDIT_LOG_LEVEL)

    app = Flask(__name__, static_folder=static_folder)
    app.config.from_object(settings)
    app.debug = settings.DEBUG

    if settings.SSLIFY and not settings.DEBUG:
        SSLify(app, skips=["healthcheck"])

    @app.before_request
    def _before_request():
        g.csp_nonce = stdlib_secrets.token_urlsafe(16)
        start_request_timer()

    @app.after_request
    def _add_csp_header(response):
        response.headers["Content-Security-Policy"] = _format_csp_policy(
            _build_csp_policy(g.csp_nonce),
        )
        return log_request(response)

    if settings.DYNAMODB_CREATE_TABLE:
        create_dynamodb_tables()

    app.register_blueprint(secrets.blueprint)
    app.register_blueprint(identity.blueprint)
    app.register_blueprint(groups.blueprint)
    app.register_blueprint(static_files.blueprint)

    return app
