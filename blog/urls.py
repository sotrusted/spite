# blog/urls.py

from django.conf import settings
from django.urls import path
from .views import home, PostCreateView, PostDetailView 
from django.conf.urls.static import static

urlpatterns = [
    path('', home, name='home'),
    path('post/new', PostCreateView.as_view(), name='post-create'),
        path('post/<int:pk>/', PostDetailView.as_view(), name='post-detail'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)