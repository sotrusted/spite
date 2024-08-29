# blog/urls.py

from django.conf import settings
from django.urls import path
from .views import home, PostCreateView, PostDetailView, like_post, PostListView, PostReplyView
from django.conf.urls.static import static

urlpatterns = [
    path('', home, name='home'),
    path('post/new', PostCreateView.as_view(), name='post-create'),
    path('post/<int:pk>/', PostDetailView.as_view(), name='post-detail'),
    path('like/<int:pk>/', like_post, name='like_post'),
    path('all-posts', PostListView.as_view(), name='post-list'),
    path('post/<int:pk>/reply/', PostReplyView.as_view(), name='post-reply'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
