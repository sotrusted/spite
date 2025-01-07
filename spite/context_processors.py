import lz4.frame as lz4
from itertools import chain
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
from blog.forms import PostSearchForm, CommentForm, PostForm
from asgiref.sync import sync_to_async
from django.urls import resolve

logger = logging.getLogger('spite')

def load_posts(request):
    # Check if we've shown the loading screen
    is_loading = not request.COOKIES.get('loading_complete', False)
    
    current_route = resolve(request.path_info).url_name
    if current_route == 'post-detail':
        return {
            'days_since_launch': days_since_launch(),
            'comment_form': CommentForm(),
            'is_loading': is_loading,
        }
    elif current_route == 'stream-posts':
        return { 'is_loading': is_loading }

    posts_data, posts, pinned_posts = get_posts()


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
    
 
    for post in pinned_posts:
        query_post = Post.objects.get(id=post.id)
        comments = Comment.objects.filter(post=query_post).order_by('-created_on')
        # Attach comments and total count directly to the post object
        post.comments_total = comments.count()
        post.recent_comments = comments

    
    highlight_comments = Comment.objects.all().order_by('-created_on')[:5]

    all_comments = Comment.objects.all().order_by('-created_on')

    # Combine posts and comments into a single feed
    combined_items = sorted(
        chain(posts, all_comments),
        key=lambda x: x.date_posted if hasattr(x, 'date_posted') else x.created_on,
        reverse=True
    )

    # Paginate the combined feed items
    paginator = Paginator(combined_items, 20)  # 20 items per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    for post in page_obj.object_list:
        if post.get_item_type() == 'Post':
            comments = Comment.objects.filter(post=post).order_by('-created_on')
            # Attach comments and total count directly to the post object
            post.comments_total = comments.count()
            post.recent_comments = comments



    return {
        'days_since_launch': days_since_launch(),
        'comment_form': CommentForm(),
        'search_form': PostSearchForm(), 
        'postForm': PostForm(),
        'posts': page_obj,
        'pinned_posts': posts_data['pinned_posts'],
        'spite': len(posts_data['posts']) + len(all_comments),
        'user_count': user_count_data['user_count'],
        'is_paginated': page_obj.has_other_pages(),
        'highlight_comments': highlight_comments,
        'is_loading': is_loading,
    }

def days_since_launch():
    site_launch_date = datetime(2024, 8, 23)
    current_date = datetime.now()
    days_since = (current_date - site_launch_date).days
    return days_since

def get_posts():
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

        posts = posts_data['posts']
        pinned_posts = posts_data['pinned_posts']
    return posts_data, posts, pinned_posts

