import uuid

from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

from .log_context import clear_request_context, set_request_context


class RequestContextMiddleware(MiddlewareMixin):
    """Attach request-scoped context for structured logging."""

    def process_request(self, request: HttpRequest) -> None:
        user = getattr(request, 'user', None)
        user_id = getattr(user, 'id', None) if getattr(user, 'is_authenticated', False) else None
        username = getattr(user, 'username', None) if getattr(user, 'is_authenticated', False) else 'anonymous'
        context = {
            'request_id': request.headers.get('X-Request-ID') or str(uuid.uuid4()),
            'user_id': user_id,
            'username': username,
            'http_method': request.method,
            'path': request.path,
            'remote_addr': request.META.get('REMOTE_ADDR'),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        }
        request.log_context = context
        set_request_context(context)

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        clear_request_context()
        return response

    def process_exception(self, request: HttpRequest, exception: Exception) -> None:
        clear_request_context()


