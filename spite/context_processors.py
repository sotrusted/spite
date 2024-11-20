import lz4.frame as lz4
import pickle
from blog.models import Post, Comment
import logging
from spite.count_users import count_ips
from django.core.paginator import Paginator
from django.conf import settings
import zlib
from django.core.cache import cache
from spite.tasks import cache_posts_data
from datetime import datetime, timedelta, timezone
import os
from blog.forms import PostSearchForm, CommentForm

logger = logging.getLogger('spite')

def load_posts(request):
    # Try to get posts from the cache
    compressed_posts_data = cache.get('posts_data')
    if not compressed_posts_data:
        # If no cached data, trigger Celery task to cache posts data
        logger.info("Cache is empty, fetching posts from the database.")
        cache_posts_data.delay()

        # Directly fetch posts from the database as a fallback

        pinned_posts = Post.objects.filter(is_pinned=True).order_by('-date_posted')
        posts = Post.objects.filter(is_pinned=False).order_by('-date_posted')

        logger.info(f"Fetched {pinned_posts.count()} pinned posts and {posts.count()} unpinned posts from the database.")
        posts_data = {'posts': posts, 'pinned_posts': pinned_posts}  # Fallback data
    else:
        # Load the cached posts data
        logger.info("Loaded posts from cache.")
        posts_data = pickle.loads(zlib.decompress(compressed_posts_data))

        # Decompress with LZ4
        decompressed_data = lz4.decompress(compressed_posts_data)

        # Deserialize with pickle
        posts_data = pickle.loads(decompressed_data)

    paginator = Paginator(posts, 20)  # Number to load initially
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Get or calculate user count data
    user_count_data = cache.get('user_count_data')
    if not user_count_data:
        iplog = os.path.join(settings.BASE_DIR, 'logs/django_access.log')
        current_time = datetime.now(timezone.utc)

        user_count, daily_user_count, active_sessions_count = \
            [count_ips(iplog, start_time=time) for time in \
             [None, current_time - timedelta(hours=24), current_time - timedelta(hours=1)]]

        user_count_data = {
            'user_count': user_count,
            'daily_user_count': daily_user_count,
            'active_sessions_count': active_sessions_count
        }

        cache.set('user_count_data', user_count_data, 60 * 1)

    # Add comments context
    for post in page_obj.object_list:
        comments = Comment.objects.filter(post=post).order_by('-created_on')
        # Attach comments and total count directly to the post object
        post.comments_total = comments.count()
        post.recent_comments = comments[:5]  # Attach the recent 5 comments directly to the post

    return {
        'days_since_launch': days_since_launch(),
        'posts': page_obj,
        'pinned_posts': posts_data['pinned_posts'],
        'spite': len(posts_data['posts']),
        'user_count': user_count_data['user_count'],
        'daily_user_count': user_count_data['daily_user_count'],
        'active_sessions_count': user_count_data['active_sessions_count'],
        'is_paginated': page_obj.has_other_pages(),
        'search_form': PostSearchForm(), 
        'comment_form': CommentForm(),
    }

def days_since_launch():
    site_launch_date = datetime(2024, 8, 23)
    current_date = datetime.now()
    days_since = (current_date - site_launch_date).days
    return days_since
