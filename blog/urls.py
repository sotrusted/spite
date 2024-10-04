# blog/urls.py

from django.conf import settings
from django.urls import path
from .views import (home, PostCreateView, PostDetailView, 
                    like_post, PostListView, PostReplyView, 
                    load_more_posts, reading_flyer, generate_pdf,
                    preview_pdf_template, search_results)
from django.conf.urls.static import static

urlpatterns = [
    path('', home, name='home'),
    path('post/new', PostCreateView.as_view(), name='post-create'),
    path('post/<int:pk>/', PostDetailView.as_view(), name='post-detail'),
    path('like/<int:pk>/', like_post, name='like_post'),
    path('all-posts', PostListView.as_view(), name='post-list'),
    path('post/<int:pk>/reply/', PostReplyView.as_view(), name='post-reply'),
    path('load-more-posts/', load_more_posts, name='load-more-posts'),
    path('reading/', reading_flyer, name='reading'),
    path('generate-pdf/', generate_pdf, name='generate_pdf'),
    path('preview-pdf-template/', preview_pdf_template, name='preview_pdf_template'),
    path('search/', search_results, name='search_results'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
