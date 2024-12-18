from django.core.cache import cache

class PageViewMiddleware:
    """
    Middleware to increment pageview counts in cache.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            cache.incr('pageview_temp_count', delta=1)
        except ValueError:
            # If the key doesn't exist, set it to 1
            cache.set('pageview_temp_count', 1)

        response = self.get_response(request)
        return response
