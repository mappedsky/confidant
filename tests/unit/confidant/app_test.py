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
