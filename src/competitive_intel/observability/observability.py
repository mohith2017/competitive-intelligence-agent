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


def log_model(message: str, model: BaseModel) -> None:
    """Log a typed pipeline artifact as structured attributes."""
    if _logfire is not None:
        _logfire.info(message, **model.model_dump())
