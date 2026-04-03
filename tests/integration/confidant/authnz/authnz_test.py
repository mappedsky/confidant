from confidant.app import create_app


def test_index_is_public(mocker):
    mocker.patch("confidant.settings.DEBUG", False)
    mocker.patch("confidant.settings.SSLIFY", False)
    mocker.patch("confidant.settings.OIDC_REDIRECT_URI", "")
    app = create_app()
    ret = app.test_client().get("/", follow_redirects=False)
    assert ret.status_code == 200


def test_auth_config_is_public():
    app = create_app()
    ret = app.test_client().get("/v1/auth_config", follow_redirects=False)
    assert ret.status_code == 200
    assert "auth_required" in ret.get_json()


def test_auth_failure_returns_unauthorized(mocker):
    mocker.patch("confidant.settings.USE_AUTH", True)
    mocker.patch("confidant.authnz.settings.USE_AUTH", True)
    mocker.patch(
        "confidant.authnz.settings.JWKS_URL",
        "https://idp.example.com/jwks.json",
    )
    app = create_app()
    ret = app.test_client().get("/v1/user/email", follow_redirects=False)
    assert ret.status_code == 401


def test_no_auth_mode_still_works(mocker):
    mocker.patch("confidant.settings.USE_AUTH", False)
    mocker.patch("confidant.authnz.settings.USE_AUTH", False)
    app = create_app()
    ret = app.test_client().get("/v1/user/email")
    assert ret.status_code == 200
