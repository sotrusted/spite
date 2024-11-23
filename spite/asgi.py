import os
import django
from django.core.asgi import get_asgi_application
# Set the default Django settings module for ASGI
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spite.settings')
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from blog.routing import websocket_urlpatterns


# Create the ASGI application
application = ProtocolTypeRouter({
    # HTTP requests are handled by the default Django ASGI application
    "http": get_asgi_application(),
    
    # WebSocket requests are routed via Channels
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
