import logging
import time
from typing import Any

from flask import g, request

from confidant import authnz

request_logger = logging.getLogger("confidant.request")
audit_logger = logging.getLogger("confidant.audit")


def _parse_log_level(level_name: str) -> int:
    return getattr(logging, level_name.upper(), logging.INFO)


def configure_logging(level_name: str, audit_level_name: str) -> None:
    level = _parse_log_level(level_name)
    audit_level = _parse_log_level(audit_level_name)
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(
            level=level,
            format=("%(asctime)s %(levelname)s %(name)s %(message)s"),
        )
    root_logger.setLevel(level)
    audit_logger.setLevel(audit_level)


def start_request_timer() -> None:
    g.request_started_at = time.perf_counter()


def log_request(response) -> Any:
    started_at = getattr(g, "request_started_at", None)
    duration_ms = None
    if started_at is not None:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 3)
    event = _request_context(
        {
            "event": "request",
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        }
    )
    request_logger.info("request", extra=event)
    return response


def audit_event(
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    outcome: str = "success",
    **details: Any,
) -> None:
    event = _request_context(
        {
            "event": "audit",
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "outcome": outcome,
        }
    )
    for key, value in details.items():
        if value is not None:
            event[key] = value
    audit_logger.log(audit_logger.level, "audit", extra=event)


def audit_response(
    response: Any,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    outcome: str = "success",
    **details: Any,
) -> Any:
    audit_event(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        outcome=outcome,
        **details,
    )
    return response


def _request_context(event: dict[str, Any]) -> dict[str, Any]:
    principal_type = None
    principal_name = None
    principal_email = None
    tenant_id = None
    try:
        principal = getattr(g, "current_principal", None)
        if principal is not None:
            principal_type = principal.user_type
            principal_name = principal.username
            principal_email = principal.email
            tenant_id = principal.tenant_id
        else:
            principal_name = authnz.get_logged_in_user()
    except Exception:
        principal_name = None

    if tenant_id is None:
        tenant_id = getattr(g, "tenant_id", None)

    event.update(
        {
            "method": request.method,
            "path": request.path,
            "query_string": request.query_string.decode("utf-8"),
            "remote_addr": request.headers.get(
                "X-Forwarded-For",
                request.remote_addr,
            ),
            "principal_type": principal_type,
            "principal": principal_name,
            "principal_email": principal_email,
            "tenant_id": tenant_id,
        }
    )
    return event
