import contextvars
from typing import Any

_REQUEST_CONTEXT: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar('request_context', default={})


def set_request_context(context: dict[str, Any]) -> None:
    _REQUEST_CONTEXT.set(dict(context))


def get_request_context() -> dict[str, Any]:
    return dict(_REQUEST_CONTEXT.get())


def clear_request_context() -> None:
    _REQUEST_CONTEXT.set({})

