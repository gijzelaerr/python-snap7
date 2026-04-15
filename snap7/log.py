"""Structured logging for S7 communication.

Provides a :class:`PLCLoggerAdapter` that automatically injects PLC connection
context (host, rack, slot, protocol) into log messages. This makes it easy to
filter and correlate log messages in multi-PLC environments.

Usage::

    import logging
    from snap7.log import PLCLoggerAdapter

    base_logger = logging.getLogger("snap7.client")
    logger = PLCLoggerAdapter(base_logger, plc_host="192.168.1.10", rack=0, slot=1)

    logger.info("Connected")
    # Output: [192.168.1.10 R0/S1] Connected

The adapter is used automatically by :class:`snap7.client.Client` when a
connection is established. No configuration is needed for basic use —
just configure the ``snap7`` logger as usual::

    logging.basicConfig(level=logging.INFO)

For JSON-structured output compatible with tools like ELK or Datadog,
use the :class:`JSONFormatter`::

    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logging.getLogger("snap7").addHandler(handler)
"""

import json
import logging
import time
from typing import Any, MutableMapping, Optional


class PLCLoggerAdapter(logging.LoggerAdapter[logging.Logger]):
    """Logger adapter that prepends PLC connection context to messages.

    Adds ``plc_host``, ``plc_rack``, ``plc_slot``, and ``plc_protocol``
    to the ``extra`` dict of every log record, and prefixes messages
    with ``[host R{rack}/S{slot}]``.
    """

    def __init__(
        self,
        logger: logging.Logger,
        plc_host: str = "",
        rack: int = 0,
        slot: int = 0,
        protocol: str = "",
    ) -> None:
        extra: dict[str, Any] = {
            "plc_host": plc_host,
            "plc_rack": rack,
            "plc_slot": slot,
            "plc_protocol": protocol,
        }
        super().__init__(logger, extra)
        self._prefix = f"[{plc_host} R{rack}/S{slot}]" if plc_host else ""

    def update_context(
        self,
        plc_host: Optional[str] = None,
        rack: Optional[int] = None,
        slot: Optional[int] = None,
        protocol: Optional[str] = None,
    ) -> None:
        """Update the PLC context after connecting."""
        extra = self.extra
        if extra is None:
            return
        if plc_host is not None:
            extra["plc_host"] = plc_host  # type: ignore[index]
        if rack is not None:
            extra["plc_rack"] = rack  # type: ignore[index]
        if slot is not None:
            extra["plc_slot"] = slot  # type: ignore[index]
        if protocol is not None:
            extra["plc_protocol"] = protocol  # type: ignore[index]
        host = extra.get("plc_host", "")
        r = extra.get("plc_rack", 0)
        s = extra.get("plc_slot", 0)
        self._prefix = f"[{host} R{r}/S{s}]" if host else ""

    def process(self, msg: str, kwargs: MutableMapping[str, Any]) -> tuple[str, MutableMapping[str, Any]]:
        """Prepend PLC context prefix to the message."""
        if self._prefix:
            msg = f"{self._prefix} {msg}"
        return msg, kwargs


class OperationLogger:
    """Context manager that logs operation timing at DEBUG level.

    Usage::

        with OperationLogger(logger, "db_read", db=1, start=0, size=4):
            data = connection.send_receive(request)
    """

    def __init__(self, logger: logging.Logger | PLCLoggerAdapter, operation: str, **context: Any) -> None:
        self._logger = logger
        self._operation = operation
        self._context = context
        self._start = 0.0

    def __enter__(self) -> "OperationLogger":
        self._start = time.monotonic()
        return self

    def __exit__(self, *args: Any) -> None:
        elapsed_ms = (time.monotonic() - self._start) * 1000
        ctx_str = " ".join(f"{k}={v}" for k, v in self._context.items())
        self._logger.debug(f"{self._operation} {ctx_str} ({elapsed_ms:.1f}ms)")


class JSONFormatter(logging.Formatter):
    """Format log records as single-line JSON objects.

    Includes PLC context fields (``plc_host``, ``plc_rack``, ``plc_slot``,
    ``plc_protocol``) when present in the record's extra dict.

    Output example::

        {"ts":"2024-01-15T10:30:00","level":"INFO","logger":"snap7.client",
         "msg":"Connected","plc_host":"192.168.1.10","plc_rack":0,"plc_slot":1}
    """

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key in ("plc_host", "plc_rack", "plc_slot", "plc_protocol"):
            value = getattr(record, key, None)
            if value is not None and value != "" and value != 0:
                entry[key] = value
        if record.exc_info and record.exc_info[1]:
            entry["exception"] = str(record.exc_info[1])
        return json.dumps(entry, default=str)
