# In your routing.py file
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/posts/$', consumers.PostConsumer.as_asgi()),
    re_path(r'ws/comments/$', consumers.CommentConsumer.as_asgi()),
]