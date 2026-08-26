import json
import logging
import re
import sys
from datetime import datetime, timezone

from app.core.config import get_settings

_SECRET_PATTERN = re.compile(
    r"(api[_-]?key|access[_-]?token|password|secret|authorization|bearer)\s*[:=]\s*\S+",
    re.IGNORECASE,
)


class _RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _redact(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {key: _redact_value(value) for key, value in record.args.items()}
            else:
                record.args = tuple(_redact_value(arg) for arg in record.args)
        return True


def _redact_value(value: object) -> object:
    if isinstance(value, str):
        return _redact(value)
    return value


def _redact(value: str) -> str:
    return _SECRET_PATTERN.sub("[REDACTED]", value)


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def setup_logging() -> None:
    settings = get_settings()
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(settings.log_level.upper())

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_RedactingFilter())
    if settings.is_production:
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    root.addHandler(handler)
