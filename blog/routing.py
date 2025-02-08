from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/posts/$', consumers.PostConsumer.as_asgi()),
    re_path(r'ws/comments/$', consumers.CommentConsumer.as_asgi()),
    re_path(r'ws/posts/(?P<post_id>\w+)/$', consumers.PostConsumer.as_asgi()),
    re_path(r'ws/comments/(?P<comment_id>\w+)/$', consumers.CommentConsumer.as_asgi()),
    re_path(r'ws/chat/$', consumers.ChatConsumer.as_asgi()),
]

