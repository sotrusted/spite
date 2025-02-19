import logging
from django.shortcuts import redirect
from django.urls import reverse
from urllib.parse import quote
import requests
from django.db import connection

logger = logging.getLogger('spite')

class LoadingScreenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        logger.info(f"Processing request for path: {request.path}")
        
        # Check for retry count to prevent infinite loops
        retry_count = request.session.get('loading_retry_count', 0)
        if retry_count > 3:  # Limit retries
            logger.warning("Too many retries, clearing loading state")
            request.session['loading_retry_count'] = 0
            response = self.get_response(request)
            response.set_cookie('loading_complete', 'true', path='/')
            return response

        # Skip conditions
        if any([
            'page' in request.GET,
            request.path.startswith('/static/'),
            request.path.startswith('/media/'),
            request.path.startswith('/hx/'),
            request.path == reverse('loading-screen'),
            request.headers.get('x-requested-with') == 'XMLHttpRequest',
            request.headers.get('HX-Request') == 'true',
            request.path.startswith('/api/'),
            'query' in request.GET,
            request.COOKIES.get('loading_complete') == 'true'  # Be explicit about the value
        ]):
            logger.info(f"Skipping - {request.path}")
            return self.get_response(request)

        # If we get here, we need to show loading screen
        request.session['loading_retry_count'] = retry_count + 1
        target_url = f"{request.path}{'?' + request.GET.urlencode() if request.GET else ''}"
        loading_url = f"{reverse('loading-screen')}?to={quote(target_url)}"
        
        logger.info(f"Redirecting to loading screen. Target URL: {target_url}")
        return redirect(loading_url)