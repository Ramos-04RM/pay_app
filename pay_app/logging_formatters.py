import json
import logging
from datetime import datetime, timezone
from typing import Any


class JsonLogFormatter(logging.Formatter):
    """Render one JSON object per line for easy ingestion by Loki/Grafana."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            'time': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec='milliseconds'),
            'level': record.levelname,
            'logger': record.name,
            'event': getattr(record, 'event', 'application.log'),
            'message': record.getMessage(),
            'username': getattr(record, 'username', 'system'),
            'user_id': getattr(record, 'user_id', None),
            'request_id': getattr(record, 'request_id', None),
            'http_method': getattr(record, 'http_method', None),
            'path': getattr(record, 'path', None),
            'remote_addr': getattr(record, 'remote_addr', None),
            'user_agent': getattr(record, 'user_agent', None),
            'context': getattr(record, 'context', {}),
        }

        if record.exc_info:
            payload['exc_info'] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=True, separators=(',', ':'))

