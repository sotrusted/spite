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
                not any(x in request.path for x in ['/static/', '/media/', '/admin/', 
                                                    '/api/', '/hx/', '/get-csrf-token/', 
                                                    '/robots.txt', '/sitemap.xml', '/sitemap.xml.gz',
                                                    '/infinite-scroll-posts/', '/serviceworker.js',
                                                    '/post/']) and
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
                except Exception:
                    # Fallback for any cache backend issues or when key doesn't exist
                    current_count = cache.get(cache_key, 0)
                    new_count = current_count + 1
                    cache.set(cache_key, new_count, 3600)  # Cache for 1 hour
                
                # Get the total from cache first, fallback to database only if needed
                cached_total = cache.get('pageview_db_total')
                if cached_total is None:
                    # Only hit database if not in cache
                    total = PageView.objects.first()
                    if not total:
                        total = PageView.objects.create(count=0)
                    cached_total = total.count
                    # Cache the DB total for 1 hour
                    cache.set('pageview_db_total', cached_total, 3600)
                
                # Store the combined count for immediate display
                cache.set('current_total_views', cached_total + new_count)
                
                logger.debug(f"Pageview tracked for {request.path} - Temp count: {new_count}, DB total: {cached_total}, Combined: {cached_total + new_count}")

        except Exception as e:
            logger.error(f"Error in PageViewMiddleware: {e}")

        response = self.get_response(request)
        return response
