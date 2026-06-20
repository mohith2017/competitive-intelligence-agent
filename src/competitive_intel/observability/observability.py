"""Observability: Logfire + OpenTelemetry tracing for every pipeline stage."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any

from pydantic import BaseModel

from ..config import Settings, get_settings

_log = logging.getLogger(__name__)

try:
    import logfire as _logfire_module
except ImportError:
    _logfire_module = None

try:
    from openinference.instrumentation.langchain import LangChainInstrumentor
except Exception:
    LangChainInstrumentor = None 

try:
    from opentelemetry import context as _otel_context
except ImportError:
    _otel_context = None

_CONFIGURED = False
_logfire: Any = None


def configure(settings: Settings | None = None) -> bool:
    """Configure Logfire + instrumentation once. Returns True if tracing is live."""
    global _CONFIGURED, _logfire
    if _CONFIGURED:
        return _logfire is not None

    settings = settings or get_settings()
    _CONFIGURED = True

    if _logfire_module is None:
        return False

    _logfire_module.configure(
        token=settings.logfire_token,
        send_to_logfire="if-token-present",
        service_name="competitive-intel",
        # Off by default to keep CLI output clean; set LOGFIRE_CONSOLE=1 to
        # also print spans to the terminal when debugging tracing.
        console=None if settings.logfire_console else False,
    )
    _logfire = _logfire_module

    if LangChainInstrumentor is not None:
        try:
            LangChainInstrumentor().instrument()
        except Exception:
            _log.debug("LangChain instrumentation failed to initialize", exc_info=True)

    for instrument in ("instrument_httpx", "instrument_requests"):
        try:
            getattr(_logfire, instrument)()
        except Exception:
            _log.debug("logfire.%s() failed to initialize", instrument, exc_info=True)

    return True


@contextmanager
def span(name: str, **attributes: Any):
    """Open a Logfire span for a pipeline stage (no-op if tracing is off)."""
    if _logfire is not None:
        with _logfire.span(name, **attributes) as current:
            yield current
    else:
        yield None


def current_context() -> Any:
    """Capture the active OTel context so it can be re-attached in a thread."""
    if _otel_context is not None:
        return _otel_context.get_current()
    return None


@contextmanager
def use_context(ctx: Any):
    """
    Re-attach a captured OTel context (e.g. inside a worker thread).
    """
    if _otel_context is not None and ctx is not None:
        token = _otel_context.attach(ctx)
        try:
            yield
        finally:
            _otel_context.detach(token)
    else:
        yield


def log_model(message: str, model: BaseModel) -> None:
    """Log a typed pipeline artifact as structured attributes."""
    if _logfire is not None:
        _logfire.info(message, **model.model_dump())


def flush() -> None:
    if _logfire is not None:
        try:
            _logfire.force_flush()
        except Exception:
            _log.debug("logfire.force_flush() failed", exc_info=True)
