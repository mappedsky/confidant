from confidant.app import create_app


def test_oidc_callback_restarts_on_vite_dev_server_in_debug(mocker):
    mocker.patch("confidant.settings.DEBUG", True)
    mocker.patch("confidant.settings.STATIC_FOLDER", "public")
    mocker.patch(
        "confidant.settings.OIDC_REDIRECT_URI",
        "http://localhost:3000/auth/callback",
    )

    app = create_app()
    ret = app.test_client().get(
        "/auth/callback?code=test-code",
        follow_redirects=False,
    )

    assert ret.status_code == 302
    assert ret.location == "http://localhost:3000/"


def test_spa_routes_redirect_to_vite_dev_server_in_debug(mocker):
    mocker.patch("confidant.settings.DEBUG", True)
    mocker.patch("confidant.settings.STATIC_FOLDER", "public")
    mocker.patch(
        "confidant.settings.OIDC_REDIRECT_URI",
        "http://localhost:3000/auth/callback",
    )

    app = create_app()
    ret = app.test_client().get(
        "/groups?tab=all",
        follow_redirects=False,
    )

    assert ret.status_code == 302
    assert ret.location == "http://localhost:3000/groups?tab=all"


def test_spa_routes_serve_index_when_not_redirecting_to_vite(mocker):
    mocker.patch("confidant.settings.DEBUG", False)
    mocker.patch("confidant.settings.SSLIFY", False)
    mocker.patch("confidant.settings.STATIC_FOLDER", "public")
    mocker.patch("confidant.settings.OIDC_REDIRECT_URI", "")

    app = create_app()
    ret = app.test_client().get("/groups", follow_redirects=False)

    assert ret.status_code == 200
    assert b'<div id="root"></div>' in ret.data
    assert b"%CSP_NONCE%" not in ret.data
    nonce = _get_nonce_from_csp(ret.headers["Content-Security-Policy"])
    assert nonce.encode("utf-8") in ret.data


def test_spa_routes_do_not_redirect_to_non_local_origins(mocker):
    mocker.patch("confidant.settings.DEBUG", True)
    mocker.patch("confidant.settings.STATIC_FOLDER", "public")
    mocker.patch(
        "confidant.settings.OIDC_REDIRECT_URI",
        "https://evil.example.com/auth/callback",
    )

    app = create_app()
    ret = app.test_client().get("/groups", follow_redirects=False)

    assert ret.status_code == 200
    assert b'<div id="root"></div>' in ret.data


def test_spa_routes_set_nonce_based_csp_header(mocker):
    mocker.patch("confidant.settings.DEBUG", False)
    mocker.patch("confidant.settings.SSLIFY", False)
    mocker.patch("confidant.settings.STATIC_FOLDER", "public")
    mocker.patch("confidant.settings.OIDC_REDIRECT_URI", "")
    mocker.patch(
        "confidant.app.stdlib_secrets.token_urlsafe",
        return_value="test-nonce",
    )

    app = create_app()
    ret = app.test_client().get("/groups", follow_redirects=False)

    csp = ret.headers["Content-Security-Policy"]
    assert ret.status_code == 200
    assert "style-src 'self' 'nonce-test-nonce'" in csp
    assert "'unsafe-inline'" not in csp


def _get_nonce_from_csp(csp):
    for directive in csp.split("; "):
        if not directive.startswith("style-src "):
            continue
        for source in directive.split()[1:]:
            if source.startswith("'nonce-") and source.endswith("'"):
                return source.removeprefix("'nonce-").removesuffix("'")
    raise AssertionError("style-src nonce not found")
