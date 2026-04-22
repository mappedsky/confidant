import logging

from confidant.app import create_app


def test_create_app_initializes_dynamodb_tables_when_enabled(mocker):
    mocker.patch("confidant.settings.DYNAMODB_CREATE_TABLE", True)
    init_mock = mocker.patch("confidant.app.create_dynamodb_tables")

    create_app()

    init_mock.assert_called_once_with()


def test_create_app_skips_dynamodb_tables_when_disabled(mocker):
    mocker.patch("confidant.settings.DYNAMODB_CREATE_TABLE", False)
    init_mock = mocker.patch("confidant.app.create_dynamodb_tables")

    create_app()

    init_mock.assert_not_called()


def test_create_app_logs_requests(caplog, mocker):
    app = create_app()
    mocker.patch("confidant.settings.USE_AUTH", False)

    with caplog.at_level(logging.INFO, logger="confidant.request"):
        ret = app.test_client().get("/healthcheck")

    assert ret.status_code == 200
    record = caplog.records[-1]
    assert record.event == "request"
    assert record.method == "GET"
    assert record.path == "/healthcheck"
    assert record.status_code == 200
    assert record.duration_ms is not None


def test_create_app_configures_audit_logger_level(mocker):
    mocker.patch("confidant.settings.AUDIT_LOG_LEVEL", "WARNING")

    create_app()

    assert logging.getLogger("confidant.audit").level == logging.WARNING
