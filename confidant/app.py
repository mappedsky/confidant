import logging
from urllib.parse import urlparse

import boto3
import guard
from flask import Flask
from flask_sslify import SSLify

from confidant import settings
from confidant.routes import credentials
from confidant.routes import identity
from confidant.routes import services
from confidant.routes import static_files
from confidant.utils.dynamodb import create_dynamodb_tables

if not settings.get("DEBUG"):
    boto3.set_stream_logger(level=logging.CRITICAL)
    logging.getLogger("botocore").setLevel(logging.CRITICAL)


def _build_csp_policy():
    policy = {
        "default-src": ["'self'"],
        "connect-src": ["'self'"],
        "style-src": ["'self'", "'unsafe-inline'"],  # for spin.js
    }
    if settings.OIDC_AUTHORITY:
        parsed = urlparse(settings.OIDC_AUTHORITY)
        oidc_origin = f"{parsed.scheme}://{parsed.netloc}"
        if oidc_origin not in policy["connect-src"]:
            policy["connect-src"].append(oidc_origin)
        policy["frame-src"] = [oidc_origin]
    return policy


def create_app():
    static_folder = settings.STATIC_FOLDER

    app = Flask(__name__, static_folder=static_folder)
    app.config.from_object(settings)
    app.config.update(settings.encrypted_settings.get_all_secrets())
    app.debug = settings.DEBUG

    if settings.SSLIFY and not settings.DEBUG:
        SSLify(app, skips=["healthcheck"])

    app.wsgi_app = guard.ContentSecurityPolicy(
        app.wsgi_app,
        _build_csp_policy(),
    )

    if settings.REDIS_URL_FLASK_SESSIONS:
        import redis
        from flask_session import Session

        app.config["SESSION_REDIS"] = redis.Redis.from_url(
            settings.REDIS_URL_FLASK_SESSIONS,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
        )
        Session(app)

    app.secret_key = settings.SESSION_SECRET

    if settings.DYNAMODB_CREATE_TABLE:
        create_dynamodb_tables()

    app.register_blueprint(credentials.blueprint)
    app.register_blueprint(identity.blueprint)
    app.register_blueprint(services.blueprint)
    app.register_blueprint(static_files.blueprint)

    return app
