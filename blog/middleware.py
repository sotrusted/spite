from django.core.exceptions import PermissionDenied
from django.utils import timezone
from .models import BlockedIP
import logging
import ipaddress
from django.core.cache import cache
from django.http import HttpResponseForbidden
from django.db.models import Q

logger = logging.getLogger('spite')

class BlockIPMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.cache_key = 'blocked_ips'
        self.cache_timeout = 3600  # 1 hour - shorter for testing

    def get_blocked_ips(self):
        blocked = cache.get(self.cache_key)
        if blocked is None:
            # Get all active blocked IPs
            blocked_entries = BlockedIP.objects.all().values('ip_address', 'ip_range')
            
            # Separate into individual IPs and ranges
            individual_ips = []
            ip_ranges = []
            
            for entry in blocked_entries:
                if entry.get('ip_address'):
                    individual_ips.append(entry['ip_address'])
                elif entry.get('ip_range'):
                    ip_ranges.append(entry['ip_range'])
            
            # Filter out None values
            individual_ips = [ip for ip in individual_ips if ip is not None]
            ip_ranges = [ip_range for ip_range in ip_ranges if ip_range is not None]
            
            blocked = {
                'ips': individual_ips,
                'ranges': ip_ranges
            }
            
            cache.set(self.cache_key, blocked, self.cache_timeout)
        return blocked

    def __call__(self, request):
        ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR')
        
        blocked = self.get_blocked_ips()
        individual_ips = blocked.get('ips', [])
        ip_ranges = blocked.get('ranges', [])
        
        try:
            ip_obj = ipaddress.ip_address(ip)
            
            # Check individual IPs
            for blocked_ip in individual_ips:
                # Direct IP match
                if ip == blocked_ip:
                    logger.warning(f"Blocked request from IP: {ip}")
                    return HttpResponseForbidden("Access denied.")
                    
                # CIDR notation check for individual IPs
                if '/' in blocked_ip:
                    try:
                        network = ipaddress.ip_network(blocked_ip, strict=False)
                        if ip_obj in network:
                            logger.warning(f"Blocked request from IP: {ip} (matched CIDR: {blocked_ip})")
                            return HttpResponseForbidden("Access denied.")
                    except ValueError:
                        logger.error(f"Invalid IP format in blocked list: {blocked_ip}")
            
            # Check IP ranges
            for ip_range in ip_ranges:
                # Handle CIDR notation in ranges
                if '/' in ip_range:
                    try:
                        network = ipaddress.ip_network(ip_range, strict=False)
                        if ip_obj in network:
                            logger.warning(f"Blocked request from IP: {ip} (matched range: {ip_range})")
                            return HttpResponseForbidden("Access denied.")
                    except ValueError:
                        logger.error(f"Invalid IP range format: {ip_range}")
                
                # Handle dash notation (e.g., "192.168.1.1-192.168.1.10")
                elif '-' in ip_range:
                    try:
                        start_ip, end_ip = ip_range.split('-')
                        start_ip_obj = ipaddress.ip_address(start_ip.strip())
                        end_ip_obj = ipaddress.ip_address(end_ip.strip())
                        
                        if start_ip_obj <= ip_obj <= end_ip_obj:
                            logger.warning(f"Blocked request from IP: {ip} (in range: {ip_range})")
                            return HttpResponseForbidden("Access denied.")
                    except ValueError as e:
                        logger.error(f"Error parsing IP range {ip_range}: {e}")
                
        except ValueError as e:
            logger.error(f"Error checking IP {ip}: {e}")
        
        return self.get_response(request)



import traceback


class HtmxDebugMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Log HTMX request details
        if request.headers.get('HX-Request'):
            logger.info(f"HTMX Request: {request.method} {request.path}")
            logger.info(f"HTMX Headers: {dict([(k, v) for k, v in request.headers.items() if k.startswith('HX-')])}")
        
        try:
            response = self.get_response(request)
            
            # Log HTMX response details
            if request.headers.get('HX-Request'):
                logger.info(f"HTMX Response: {response.status_code}")
            
            return response
        except Exception as e:
            logger.error(f"Exception in request {request.path}: {str(e)}")
            logger.error(traceback.format_exc())
            raise