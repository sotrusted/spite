import logging
from django.shortcuts import redirect
from django.urls import reverse
from urllib.parse import quote

logger = logging.getLogger('spite')

class LoadingScreenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        logger.info(f"Processing request for path: {request.path}")
        logger.info(f"Cookies present: {request.COOKIES}")
        
        # Skip conditions with logging
        if request.path.startswith('/static/'):
            logger.info("Skipping - static file")
            return self.get_response(request)
            
        if request.path.startswith('/media/'):
            logger.info("Skipping - media file")
            return self.get_response(request)
            
        if request.path == reverse('loading-screen'):
            logger.info("Skipping - already on loading screen")
            return self.get_response(request)
            
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            logger.info("Skipping - AJAX request")
            return self.get_response(request)
            
        if request.path.startswith('/api/'):
            logger.info("Skipping - API request")
            return self.get_response(request)
            
        if request.COOKIES.get('loading_complete'):
            logger.info("Skipping - loading already completed")
            return self.get_response(request)

        # If we get here, we need to show loading screen
        target_url = request.path
        loading_url = f"{reverse('loading-screen')}?to={quote(target_url)}"
        
        logger.info(f"Redirecting to loading screen. Target URL: {target_url}")
        logger.info(f"Full loading URL: {loading_url}")
        
        return redirect(loading_url)