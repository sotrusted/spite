import uuid
from django.utils import timezone
from .models import CustomUser 

class SessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        session_id = request.COOKIES.get('session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            user = CustomUser.objects.create(session_id=session_id)
        else:
            try:
                user = CustomUser.objects.get(session_id=session_id)
                user.last_active = timezone.now()
                user.save()
            except CustomUser.DoesNotExist:
                session_id = str(uuid.uuid4())
                user = CustomUser.objects.create(session_id=session_id)

        request.user = user

        response = self.get_response(request)
        response.set_cookie('session_id', session_id, httponly=True)
        return response
