# blog/urls.py

from django.conf import settings
from django.urls import path
from .views import (home, PostCreateView, PostDetailView, 
                    like_post, PostListView, PostReplyView, 
                    load_more_posts, reading_flyer, generate_pdf,
                    preview_pdf_template, search_results,
                    store_page, add_comment, get_csrf_token, 
                    offline_view, all_posts)
from django.conf.urls.static import static
from graphene_django.views import GraphQLView
from spite.schema import schema 
from django.contrib.sitemaps.views import sitemap
from .sitemaps import StaticViewSitemap, PostSitemap

sitemaps = {
    'posts': PostSitemap,
    'static': StaticViewSitemap,
}

urlpatterns = [
    path('', home, name='home'),
    path('post/new', PostCreateView.as_view(), name='post-create'),
    path('post/<int:pk>/', PostDetailView.as_view(), name='post-detail'),
    path('like/<int:pk>/', like_post, name='like_post'),
    path('all-posts', PostListView.as_view(), name='post-list'),
    path('catalog', all_posts, name='catalog'),
    path('post/<int:pk>/reply/', PostReplyView.as_view(), name='post-reply'),
    path('load-more-posts/', load_more_posts, name='load-more-posts'),
    path('reading/', reading_flyer, name='reading'),
    path('generate-pdf/', generate_pdf, name='generate_pdf'),
    path('preview-pdf-template/', preview_pdf_template, name='preview_pdf_template'),
    path('search/', search_results, name='search_results'),
    path('shop/', store_page, name='shop'),
    path('add-comment/<int:post_id>/', add_comment, name='add_comment'),
    path('get-csrf-token/', get_csrf_token, name='get_csrf_token'), 
    path("graphql/", GraphQLView.as_view(graphiql=True, schema=schema)),
    path('offline/', offline_view, name='offline'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('sitemap.xml.gz', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap_gz'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
