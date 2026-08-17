import time
import logging
from django.db import connection
from django.http import JsonResponse

logger = logging.getLogger(__name__)

class DatabaseRetryMiddleware:
    """
    Middleware to handle DB connection errors and retry.
    Handles both SQLite locking and MySQL 'Server has gone away'.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        max_retries = 3
        retry_delay = 0.2

        for attempt in range(max_retries):
            try:
                response = self.get_response(request)
                return response
            except Exception as e:
                error_msg = str(e).lower()
                is_retryable = (
                    'database is locked' in error_msg
                    or 'database locked' in error_msg
                    or 'server has gone away' in error_msg
                    or 'lost connection to mysql' in error_msg
                    or '(2006,' in error_msg   # MySQL error code for gone away
                    or '(2013,' in error_msg   # MySQL error code for lost connection
                )
                if is_retryable and attempt < max_retries - 1:
                    logger.warning(
                        f"DB connection error (attempt {attempt + 1}/{max_retries}): {e} — retrying"
                    )
                    # Close stale connection so Django opens a fresh one
                    try:
                        from django.db import connection
                        connection.close()
                    except Exception:
                        pass
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                raise

        return self.get_response(request)

    def process_exception(self, request, exception):
        error_msg = str(exception).lower()
        if 'database is locked' in error_msg or 'database locked' in error_msg:
            logger.error(f"Database locked exception: {exception}")
            if request.headers.get('Content-Type') == 'application/json' or request.path.startswith('/api/'):
                return JsonResponse({
                    'success': False,
                    'error': 'Database is temporarily busy. Please try again.'
                }, status=503)
        return None


class DatabaseConnectionMiddleware:
    """
    Middleware to ensure proper database connection handling.
    NOTE: connection.close() intentionally removed — it was killing CONN_MAX_AGE
    connection reuse and causing 'Server has gone away' on cold starts.
    Django's own connection management handles cleanup correctly.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        return None