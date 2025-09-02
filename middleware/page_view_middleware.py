from django.core.cache import cache
import logging
from blog.models import PageView
from django.utils.timezone import now

logger = logging.getLogger('spite')

class PageViewMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            # Only track GET requests to actual pages, excluding:
            # - Static/media files
            # - Admin interface
            # - API endpoints
            # - HTMX endpoints (/hx/)
            # - AJAX/HTMX requests (by headers)
            # - Pagination requests (page= parameter)
            should_track = (
                request.method == 'GET' and 
                not any(x in request.path for x in ['/static/', '/media/', '/admin/', '/api/', '/hx/']) and
                not request.headers.get('HX-Request') and
                not request.headers.get('x-requested-with') == 'XMLHttpRequest' and
                'page=' not in request.GET.urlencode()
            )
            
            if should_track:
                # Use atomic increment to avoid race conditions
                cache_key = 'pageview_temp_count'
                try:
                    # Try to increment atomically (Redis supports this)
                    new_count = cache.incr(cache_key)
                except (AttributeError, TypeError):
                    # Fallback for non-Redis cache backends
                    current_count = cache.get(cache_key, 0)
                    new_count = current_count + 1
                    cache.set(cache_key, new_count)
                
                # Get the total from database
                total = PageView.objects.first()
                if not total:
                    total = PageView.objects.create(count=0)
                
                # Store the combined count for immediate display
                cache.set('current_total_views', total.count + new_count)
                
                logger.debug(f"Pageview tracked for {request.path} - Temp count: {new_count}, DB total: {total.count}, Combined: {total.count + new_count}")

        except Exception as e:
            logger.error(f"Error in PageViewMiddleware: {e}")

        response = self.get_response(request)
        return response
