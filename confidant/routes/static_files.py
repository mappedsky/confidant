import logging
import os
from urllib.parse import urlparse

from flask import blueprints, current_app, g, redirect, request, send_from_directory
from werkzeug.exceptions import NotFound

from confidant import settings

logger = logging.getLogger(__name__)
blueprint = blueprints.Blueprint("static_files", __name__)
_FRONTEND_DEV_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _get_frontend_dev_origin():
    if not settings.DEBUG or settings.STATIC_FOLDER not in {
        "public",
        "../public",
    }:
        return None
    redirect_uri = settings.OIDC_REDIRECT_URI
    if not redirect_uri:
        return None
    parsed = urlparse(redirect_uri)
    if (
        not parsed.scheme
        or not parsed.netloc
        or parsed.scheme not in {"http", "https"}
        or parsed.hostname not in _FRONTEND_DEV_HOSTS
        or parsed.port not in {3000}
    ):
        return None
    return "http://localhost:3000"


def _redirect_to_frontend_dev_server():
    origin = _get_frontend_dev_origin()
    if not origin:
        return None
    location = f"{origin}{request.path}"
    if request.query_string:
        query_string = request.query_string.decode("utf-8")
        location = f"{location}?{query_string}"
    return redirect(location)


def _serve_spa_index():
    redirect_response = _redirect_to_frontend_dev_server()
    if redirect_response is not None:
        return redirect_response
    return _render_static_html("index.html")


def _render_static_html(filename):
    html_paths = [os.path.join(current_app.static_folder, filename)]
    if filename == "index.html":
        html_paths.append(os.path.join(current_app.root_path, "..", filename))

    for html_path in html_paths:
        if not os.path.isfile(html_path):
            continue
        with open(html_path, encoding="utf-8") as html_file:
            html = html_file.read()
        html = html.replace("%CSP_NONCE%", g.csp_nonce)
        return current_app.response_class(html, mimetype="text/html")

    raise FileNotFoundError(html_paths[0])


@blueprint.route("/")
def index():
    return _serve_spa_index()


@blueprint.route("/secrets")
@blueprint.route("/secrets/<path:path>")
@blueprint.route("/groups")
@blueprint.route("/groups/<path:path>")
def spa_routes(path=None):
    del path
    return _serve_spa_index()


@blueprint.route("/auth/callback")
def oidc_callback():
    origin = _get_frontend_dev_origin()
    if origin is not None:
        # Never forward OIDC callback query parameters across origins in
        # development. oidc-client-ts stores PKCE/OIDC state per-origin, so
        # moving `code` and `state` from :80 to :3000 causes a redirect loop.
        return redirect(f"{origin}/")
    return _render_static_html("index.html")


@blueprint.route("/loggedout")
def goodbye():
    return current_app.send_static_file("goodbye.html")


@blueprint.route("/healthcheck")
def healthcheck():
    return "", 200


@blueprint.route("/favicon.ico")
def favicon():
    return current_app.send_static_file("favicon.ico")


@blueprint.route("/404.html")
def not_found():
    return current_app.send_static_file("404.html")


@blueprint.route("/robots.txt")
def robots():
    return current_app.send_static_file("robots.txt")


@blueprint.route("/assets/<path:path>")
def assets(path):
    return current_app.send_static_file(os.path.join("assets", path))


@blueprint.route("/components/<path:path>")
@blueprint.route("/bower_components/<path:path>")
def components(path):
    return current_app.send_static_file(os.path.join("components", path))


@blueprint.route("/modules/<path:path>")
def modules(path):
    return current_app.send_static_file(os.path.join("modules", path))


@blueprint.route("/styles/<path:path>")
def static_proxy(path):
    return current_app.send_static_file(os.path.join("styles", path))


@blueprint.route("/scripts/<path:path>")
def scripts(path):
    return current_app.send_static_file(os.path.join("scripts", path))


@blueprint.route("/fonts/<path:path>")
def fonts(path):
    return current_app.send_static_file(os.path.join("fonts", path))


@blueprint.route("/images/<path:path>")
def images(path):
    return current_app.send_static_file(os.path.join("images", path))


@blueprint.route("/custom/modules/<path:path>")
def custom_modules(path):
    if not settings.CUSTOM_FRONTEND_DIRECTORY:
        return "", 200
    try:
        custom_modules_dir = os.path.join(
            settings.CUSTOM_FRONTEND_DIRECTORY,
            "modules",
        )
        return send_from_directory(custom_modules_dir, path)
    except NotFound:
        logger.warning(f"Client requested missing custom module {path}.")
        return "", 200


@blueprint.route("/custom/styles/<path:path>")
def custom_styles(path):
    if not settings.CUSTOM_FRONTEND_DIRECTORY:
        return "", 404
    custom_styles_dir = os.path.join(
        settings.CUSTOM_FRONTEND_DIRECTORY,
        "styles",
    )
    return send_from_directory(custom_styles_dir, path)


@blueprint.route("/custom/images/<path:path>")
def custom_images(path):
    if not settings.CUSTOM_FRONTEND_DIRECTORY:
        return "", 404
    custom_images_dir = os.path.join(
        settings.CUSTOM_FRONTEND_DIRECTORY,
        "images",
    )
    return send_from_directory(custom_images_dir, path)
