from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/posts/$', consumers.PostConsumer.as_asgi()),  # WebSocket route
    re_path(r'ws/comments/$', consumers.CommentConsumer.as_asgi()),  # WebSocket route for comments
    re_path(r'ws/chat/$', consumers.ChatConsumer.as_asgi()),  # WebSocket route for chat
]
