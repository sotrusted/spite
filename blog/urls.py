# blog/urls.py

from django.conf import settings
from django.urls import path
from .views import home, PostCreateView, PostDetailView, like_post 
from django.conf.urls.static import static

urlpatterns = [
    path('', home, name='home'),
    path('post/new', PostCreateView.as_view(), name='post-create'),
    path('post/<int:pk>/', PostDetailView.as_view(), name='post-detail'),
    path('like/<int:pl>/', like_post, name='like_post'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
