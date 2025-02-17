from django.core.exceptions import PermissionDenied
from django.utils import timezone
from .models import BlockedIP
import logging
import ipaddress
from django.core.cache import cache

logger = logging.getLogger('spite')

class BlockIPMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.cache_key = 'blocked_ips'
        self.cache_timeout = 3600000  # 1000 hours

    def get_blocked_ips(self):
        blocked = cache.get(self.cache_key)
        if blocked is None:
            blocked = list(BlockedIP.objects.filter(
                is_permanent=True
            ) | BlockedIP.objects.filter(
                expires__gt=timezone.now()
            ))
            cache.set(self.cache_key, blocked, self.cache_timeout)
        return blocked


    def __call__(self, request):
        ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
        
        try:
            blocked_ips = self.get_blocked_ips()

            for entry in blocked_ips:
                if entry.is_ip_blocked(ip):
                    logger.warning(f"Blocked request from IP: {ip}")
                    raise PermissionDenied("Access denied.")

        except BlockedIP.DoesNotExist:
            pass

        return self.get_response(request) 


