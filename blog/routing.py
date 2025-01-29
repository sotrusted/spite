from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/post/(?P<post_id>\w+)/$', consumers.PostConsumer.as_asgi()),
    re_path(r'ws/comment/(?P<comment_id>\w+)/$', consumers.CommentConsumer.as_asgi()),
    re_path(r'ws/chat/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/stream/(?P<stream_id>[^/]+)/$', consumers.LiveStreamConsumer.as_asgi()),
]
