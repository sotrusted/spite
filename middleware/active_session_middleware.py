# middleware/active_session_middleware.py

from django.conf import settings
from django.contrib.sessions.models import Session
from django.utils.deprecation import MiddlewareMixin

class ActiveSessionMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not hasattr(settings, 'ACTIVE_SESSION_COUNT'):
            settings.ACTIVE_SESSION_COUNT = 0

        session_key = request.session.session_key
        if session_key:
            try:
                session = Session.objects.get(session_key=session_key)
                if not session.expire_date or session.expire_date > timezone.now():
                    return
            except Session.DoesNotExist:
                pass

        request.session.create()
        settings.ACTIVE_SESSION_COUNT += 1

    def process_response(self, request, response):
        session_key = request.session.session_key
        if session_key:
            try:
                session = Session.objects.get(session_key=session_key)
                if session.expire_date and session.expire_date <= timezone.now():
                    settings.ACTIVE_SESSION_COUNT -= 1
                    session.delete()
            except Session.DoesNotExist:
                pass

        return response
