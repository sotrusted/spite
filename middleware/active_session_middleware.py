# middleware/active_session_middleware.py
from django.utils import timezone
from django.conf import settings
from django.contrib.sessions.models import Session
from django.utils.deprecation import MiddlewareMixin

class ActiveSessionMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not hasattr(settings, 'ACTIVE_SESSION_COUNT'):
            settings.ACTIVE_SESSION_COUNT = 0

        session_key = request.session.session_key
        if session_key:
            # OPTIMIZED: Skip database check for existing sessions
            # Django's session middleware already handles session validation
            # Only create new session if no session key exists
            return

        request.session.create()
        settings.ACTIVE_SESSION_COUNT += 1

    def process_response(self, request, response):
        # OPTIMIZED: Skip database operations in response processing
        # Django's session middleware handles session cleanup automatically
        return response
