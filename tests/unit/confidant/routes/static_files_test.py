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
        "/services?tab=all",
        follow_redirects=False,
    )

    assert ret.status_code == 302
    assert ret.location == "http://localhost:3000/services?tab=all"


def test_spa_routes_serve_index_when_not_redirecting_to_vite(mocker):
    mocker.patch("confidant.settings.DEBUG", False)
    mocker.patch("confidant.settings.SSLIFY", False)
    mocker.patch("confidant.settings.STATIC_FOLDER", "public")
    mocker.patch("confidant.settings.OIDC_REDIRECT_URI", "")

    app = create_app()
    ret = app.test_client().get("/services", follow_redirects=False)

    assert ret.status_code == 200
    assert b'<div id="root"></div>' in ret.data
