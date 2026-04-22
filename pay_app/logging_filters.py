import logging

from .log_context import get_request_context


class RequestContextFilter(logging.Filter):
    """Inject request metadata into each log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        context = get_request_context()

        record.request_id = getattr(record, 'request_id', context.get('request_id'))
        record.user_id = getattr(record, 'user_id', context.get('user_id'))
        record.username = getattr(record, 'username', context.get('username', 'system'))
        record.http_method = getattr(record, 'http_method', context.get('http_method'))
        record.path = getattr(record, 'path', context.get('path'))
        record.remote_addr = getattr(record, 'remote_addr', context.get('remote_addr'))
        record.user_agent = getattr(record, 'user_agent', context.get('user_agent'))
        record.event = getattr(record, 'event', 'application.log')
        record.context = getattr(record, 'context', {})
        return True

