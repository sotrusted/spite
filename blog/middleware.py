from django.core.exceptions import PermissionDenied
from django.utils import timezone
from .models import BlockedIP
import logging

logger = logging.getLogger('spite')

class BlockIPMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
        
        try:
            blocked = BlockedIP.objects.get(ip_address=ip)
            if blocked.is_active:
                logger.warning(f"Blocked request from IP: {ip}")
                raise PermissionDenied("Access denied.")
        except BlockedIP.DoesNotExist:
            pass

        return self.get_response(request) 