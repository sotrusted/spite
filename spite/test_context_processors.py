from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware

def create_test_request():
    # Create request factory
    factory = RequestFactory()
    
    # Create a GET request
    request = factory.get('/')
    
    # Add session
    middleware = SessionMiddleware(lambda x: None)
    middleware.process_request(request)
    request.session.save()
    
    # Add messages
    middleware = MessageMiddleware(lambda x: None)
    middleware.process_request(request)
    
    # Add other common attributes
    request.user = None
    request.META = {
        'REMOTE_ADDR': '127.0.0.1',
        'HTTP_X_FORWARDED_FOR': None,
        'HTTP_USER_AGENT': 'Mozilla/5.0',
    }
    
    # Add GET and POST dictionaries
    request.GET = {}
    request.POST = {}
    
    return request

# Usage example:
def test_context_processor():
    request = create_test_request()
    
    # Test your context processor
    from spite.context_processors import load_posts
    context = load_posts(request)
    
    assert 'posts' in context
    assert 'pinned_posts' in context
    return context