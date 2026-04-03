import logging
from dataclasses import dataclass
from functools import wraps
from typing import Any

import jwt
from flask import abort
from flask import g
from flask import redirect
from flask import request
from flask import url_for
from jwt import PyJWKClient

from confidant import settings
from confidant.authnz.errors import AuthenticationError
from confidant.authnz.errors import NotAuthorized
from confidant.authnz.errors import UserUnknownError

logger = logging.getLogger(__name__)

_JWKS_CLIENT: PyJWKClient | None = None


@dataclass(frozen=True)
class RequestPrincipal:
    user_type: str
    username: str
    email: str | None
    tenant_id: str | None
    jwt_claims: dict[str, Any]


def _get_jwks_client() -> PyJWKClient:
    global _JWKS_CLIENT
    if _JWKS_CLIENT is None:
        _JWKS_CLIENT = PyJWKClient(settings.JWKS_URL, cache_keys=True)
    return _JWKS_CLIENT


def _normalize_optional_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value:
        return None
    return value


def _get_required_claim(payload: dict[str, Any], claim_name: str) -> str:
    value = _normalize_optional_string(payload.get(claim_name))
    if value is None:
        raise AuthenticationError(f"Missing required JWT claim {claim_name!r}")
    return value


def _decode_jwt(token: str) -> dict[str, Any]:
    client = _get_jwks_client()
    signing_key = client.get_signing_key_from_jwt(token)
    decode_kwargs: dict[str, Any] = {
        "algorithms": settings.ALLOWED_JWT_ALGORITHMS,
    }
    if settings.JWT_ISSUER:
        decode_kwargs["issuer"] = settings.JWT_ISSUER
    if settings.JWT_AUDIENCE:
        decode_kwargs["audience"] = settings.JWT_AUDIENCE
    else:
        decode_kwargs["options"] = {"verify_aud": False}
    return jwt.decode(token, signing_key.key, **decode_kwargs)


def _read_bearer_token_from_request() -> str | None:
    header_name = settings.JWT_HEADER_NAME
    raw_value = request.headers.get(header_name)
    if raw_value is None:
        return None
    raw_value = raw_value.strip()
    if not raw_value:
        raise AuthenticationError(f"Empty JWT header {header_name!r}")

    auth_scheme = f"{settings.JWT_HEADER_PREFIX} "
    token_start = len(auth_scheme)
    is_authorization_header = header_name.lower() == "authorization"
    if is_authorization_header:
        if not raw_value.lower().startswith(auth_scheme.lower()):
            raise AuthenticationError("Authorization header must use Bearer.")
        token = raw_value[token_start:].strip()
        if not token:
            raise AuthenticationError("Bearer token is missing.")
        return token

    if raw_value.lower().startswith(auth_scheme.lower()):
        raw_value = raw_value[token_start:].strip()
    if not raw_value:
        raise AuthenticationError(
            f"JWT header {header_name!r} did not include a token."
        )
    return raw_value


def _resolve_user_type(payload: dict[str, Any]) -> str:
    user_type = _get_required_claim(payload, settings.JWT_PRINCIPAL_TYPE_CLAIM)
    if user_type not in settings.JWT_ALLOWED_PRINCIPAL_TYPES:
        raise AuthenticationError("JWT principal type is not allowed.")
    return user_type


def _resolve_username(payload: dict[str, Any], user_type: str) -> str:
    claim_candidates = []
    if user_type == settings.JWT_USER_TYPE_VALUE:
        claim_candidates.extend(
            [
                settings.JWT_USER_PRINCIPAL_CLAIM,
                settings.JWT_EMAIL_CLAIM,
                settings.JWT_SUB_CLAIM,
            ]
        )
    elif user_type == settings.JWT_SERVICE_TYPE_VALUE:
        claim_candidates.extend(
            [
                settings.JWT_SERVICE_PRINCIPAL_CLAIM,
                settings.JWT_SUB_CLAIM,
                settings.JWT_EMAIL_CLAIM,
            ]
        )
    else:
        claim_candidates.extend(
            [
                settings.JWT_USER_PRINCIPAL_CLAIM,
                settings.JWT_SERVICE_PRINCIPAL_CLAIM,
                settings.JWT_SUB_CLAIM,
                settings.JWT_EMAIL_CLAIM,
            ]
        )

    seen = set()
    for claim_name in claim_candidates:
        if claim_name in seen:
            continue
        seen.add(claim_name)
        value = _normalize_optional_string(payload.get(claim_name))
        if value is not None:
            return value

    raise AuthenticationError(
        "Could not resolve a principal identifier from JWT claims."
    )


def _principal_from_payload(payload: dict[str, Any]) -> RequestPrincipal:
    user_type = _resolve_user_type(payload)
    username = _resolve_username(payload, user_type)
    email = _normalize_optional_string(payload.get(settings.JWT_EMAIL_CLAIM))
    tenant_id_claim = settings.JWT_TENANT_ID_CLAIM
    tenant_id = _normalize_optional_string(payload.get(tenant_id_claim))
    return RequestPrincipal(
        user_type=user_type,
        username=username,
        email=email,
        tenant_id=tenant_id,
        jwt_claims=payload,
    )


def _set_request_principal(principal: RequestPrincipal) -> None:
    g.current_principal = principal
    g.user_type = principal.user_type
    g.auth_type = "jwt"
    g.username = principal.username
    g.jwt_claims = principal.jwt_claims
    g.tenant_id = principal.tenant_id


def _get_request_principal() -> RequestPrincipal:
    principal = getattr(g, "current_principal", None)
    if principal is None:
        raise UserUnknownError()
    return principal


def get_logged_in_user():
    """
    Retrieve the normalized principal name for the authenticated request.
    """
    if not settings.USE_AUTH:
        return "unauthenticated user"
    return _get_request_principal().username


def get_logged_in_email() -> str | None:
    if not settings.USE_AUTH:
        return None
    return _get_request_principal().email


def get_tenant_id():
    if not settings.MULTI_TENANT:
        return "singletenant"
    tenant_id = _normalize_optional_string(getattr(g, "tenant_id", None))
    if tenant_id is not None:
        return tenant_id
    raise UserUnknownError()


def user_is_user_type(user_type):
    if not settings.USE_AUTH:
        return True
    return getattr(g, "user_type", None) == user_type


def user_is_service(service):
    if not settings.USE_AUTH:
        return True
    return (
        getattr(g, "user_type", None) == settings.JWT_SERVICE_TYPE_VALUE
        and getattr(g, "username", None) == service
    )


def require_csrf_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        return f(*args, **kwargs)

    return decorated


def log_in():
    return redirect(url_for("static_files.index"))


def redirect_to_logout_if_no_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        return f(*args, **kwargs)

    return decorated


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not settings.USE_AUTH:
            return f(*args, **kwargs)

        if not settings.JWKS_URL:
            logger.error("JWKS_URL required when USE_AUTH is enabled.")
            return abort(500)

        try:
            token = _read_bearer_token_from_request()
            if token is None:
                return abort(401)
            payload = _decode_jwt(token)
            principal = _principal_from_payload(payload)
            _set_request_principal(principal)
        except AuthenticationError as exc:
            logger.warning("Authentication failed: %s", exc)
            return abort(401)
        except jwt.PyJWTError as exc:
            logger.warning("JWT validation failed: %s", exc)
            return abort(401)
        except NotAuthorized as exc:
            logger.warning("Not authorized -- %s", exc)
            return abort(403)

        return f(*args, **kwargs)

    return decorated


def require_logout_for_goodbye(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        return f(*args, **kwargs)

    return decorated
