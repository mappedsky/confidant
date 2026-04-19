from confidant.utils import resource_ids


def test_validate_secret_id_rejects_leading_slash():
    assert resource_ids.validate_secret_id("/test/me") == (
        "secret id must not start with /"
    )


def test_validate_secret_id_allows_internal_slashes():
    assert resource_ids.validate_secret_id("test/me") is None
