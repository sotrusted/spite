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
            # Only track GET requests to actual pages
            if request.method == 'GET' and not any(x in request.path for x in ['/static/', '/media/', '/admin/', '/api/']):
                # Increment both counters
                cache_key = 'pageview_temp_count'
                current_count = cache.get(cache_key, 0)
                cache.set(cache_key, current_count + 1)
                
                # Get the total from database
                total = PageView.objects.first()
                if not total:
                    total = PageView.objects.create(count=0)
                
                # Store the combined count for immediate display
                cache.set('current_total_views', total.count + current_count + 1)

        except Exception as e:
            logger.error(f"Error in PageViewMiddleware: {e}")

        response = self.get_response(request)
        return response
