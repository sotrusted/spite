# blog/urls.py

from django.conf import settings
from django.urls import path
from .views import (home, PostCreateView, PostDetailView, 
                    like_post, PostListView, PostReplyView, 
                    load_more_posts, reading_flyer, generate_pdf,
                    preview_pdf_template, search_results,
                    store_page, add_comment, reply_comment, get_csrf_token, 
                    offline_view, all_posts, get_comment_form_html,
                    get_comment_reply_form_html,
                    SaveListView, get_word_cloud, download_posts_as_html_stream,
                    get_media_features, media_flow, media_flow_standalone,
                    loading_screen, log_javascript, resume, update_online_status,
                    remove_user,                     hx_get_parent_post, hx_get_comment,
                    hx_get_comment_by_id, hx_get_comment_reply_form_html,
                    hx_scroll_to_post_form, toggle_version, hx_get_post, hx_get_post_comment_section,
                    spite_tv, spite_counter, htmx_health_check, htmx_test_post, htmx_debug_view,
                    spam_monitor_view)


import blog.views as blog_views
import blog.test_views as test_views

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
    path('post/new/', PostCreateView.as_view(), name='post-create'),
    path('post/<int:pk>/', PostDetailView.as_view(), name='post-detail'),
    path('like/<int:pk>/', like_post, name='like_post'),
    path('all-posts/', PostListView.as_view(), name='post-list'),
    path('catalog/', all_posts, name='catalog'),
    path('post/<int:pk>/reply/', PostReplyView.as_view(), name='post-reply'),
    path('load-more/', load_more_posts, name='load-more-posts'),
    path('reading/', reading_flyer, name='reading'),
    path('generate-pdf/', generate_pdf, name='generate_pdf'),
    path('preview-pdf-template/', preview_pdf_template, name='preview_pdf_template'),
    path('search/', search_results, name='search_results'),
    path('shop/', store_page, name='shop'),
    path('add-comment/<int:post_id>/', add_comment, name='add-comment'),
    path('add-comment/comment/<int:comment_id>/', reply_comment, name='reply-comment'),
    path('get-csrf-token/', get_csrf_token, name='get_csrf_token'), 
    path("graphql/", GraphQLView.as_view(graphiql=True, schema=schema)),
    path('offline/', offline_view, name='offline'),
    path('sitemap.xml/', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('sitemap.xml.gz/', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap_gz'),
    path('api/get-comment-form-html/<int:post_id>/', get_comment_form_html, name='get_comment_form_html'),
    path('api/get-reply-form-html/<int:comment_id>/', get_comment_reply_form_html, name='get_comment_reply_form'),
    path('api/save-list/', SaveListView.as_view(), name='save_list'),
    path('api/word-cloud/', get_word_cloud, name='word_cloud'),
    path('stream-posts/', download_posts_as_html_stream, name='stream_posts'),
    path('api/media-features/', get_media_features, name='media-features'),
    path('media-flow/', media_flow, name='media-flow'),
    path('media-flow-standalone/', media_flow_standalone, name='media-flow-standalone'),
    path('loading/', loading_screen, name='loading-screen'),
    path('api/log-js/', log_javascript, name='log_js'),
    path('resume/', resume, name='resume'),
    path('api/online-count/', update_online_status, name='online_count'),
    path('api/remove-user/', remove_user, name='remove_user'),
    path('hx/parent-post/<int:post_id>/', hx_get_parent_post, name='hx-get-parent-post'),
    path('hx/get-comment/', hx_get_comment, name='hx-get-comment'),
    path('hx/get-comment/<int:comment_id>/', hx_get_comment_by_id, name='hx-get-comment-by-id'),
    path('hx/get-reply-form-html/<int:comment_id>/', hx_get_comment_reply_form_html, name='hx-get-reply-form-html'),
    path('hx/scroll-to-post-form/', hx_scroll_to_post_form, name='hx-scroll-to-post-form'),
    path('toggle-version/', toggle_version, name='toggle_version'),
    path('hx/get-post/<int:post_id>/', hx_get_post, name='hx-get-post'),
    path('hx/get-post-comment-section/<int:post_id>/', hx_get_post_comment_section, name='hx-get-post-comment-section'),
    path('live/', spite_tv, name='spite-tv'),
    path('hx/get-comment-chain/<int:comment_id>/', blog_views.hx_get_comment_chain, name='get-comment-chain'),
    path('editor/', test_views.editor, name='editor'),
    path('spite-counter/', spite_counter, name='spite-counter'),
    path('hx/health-check/', htmx_health_check, name='htmx-health-check'),
    path('hx/test-post/', htmx_test_post, name='htmx-test-post'),
    path('hx/debug/', htmx_debug_view, name='htmx-debug'),
    path('spam-monitor/', spam_monitor_view, name='spam-monitor'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
