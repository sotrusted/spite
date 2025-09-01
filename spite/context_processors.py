import lz4.frame as lz4
from itertools import chain
import pickle
from blog.models import Post, Comment
import logging
from spite.count_users import count_ips
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.conf import settings
import zlib
from django.core.cache import cache
from spite.tasks import cache_posts_data
from datetime import datetime, timedelta, timezone
import os
from blog.forms import PostSearchForm, CommentForm, PostForm
from asgiref.sync import sync_to_async
from django.urls import resolve
from django.shortcuts import get_object_or_404
from spite.utils import cache_large_data
from django.db.models import Prefetch
from itertools import islice

def preprocess_post(post):
    post = get_object_or_404(Post, id=post.id)
    comments = Comment.objects.filter(post=post).order_by('-created_on')
    # Attach comments and total count directly to the post object
    post.comments_total = comments.count()
    post.recent_comments = comments
    return post

def preprocess_comment(item):
    return item



logger = logging.getLogger('spite')
def get_optimized_posts():
    """Get posts with consistent cache strategy"""
    # Check for pinned posts first
    pinned_posts = cache.get('pinned_posts')
    if pinned_posts:
        pinned_posts = [DictToObject(post) for post in pickle.loads(lz4.decompress(pinned_posts))]  
    
    # Get chunk count
    chunk_count = cache.get('posts_chunk_count', 0)
    posts = []
    
    # Collect chunks
    for i in range(chunk_count):
        chunk = cache.get(f'posts_chunk_{i}')
        if chunk:
            posts.extend([DictToObject(post) for post in pickle.loads(lz4.decompress(chunk))])
    
    return {
        'posts': posts,
        'pinned_posts': pinned_posts or [],
        'has_more': len(posts) >= 20  # Assuming 20 per page
    }

def get_cached_posts(request):
    try:
        # Check cache freshness
        last_update = cache.get('last_cache_update')
        current_time = datetime.now().timestamp()
        
        # If cache is older than 1 minute or missing, force refresh
        if not last_update or (current_time - last_update) > 60:
            logger.info("Cache stale or missing, forcing refresh")
            cache_posts_data()  # Direct call for immediate refresh
            
        # Get pinned posts (usually few)
        compressed_pinned = cache.get('pinned_posts')
        pinned_posts = []
        if compressed_pinned:
            pickled_pinned = lz4.decompress(compressed_pinned)
            pinned_posts = [DictToObject(post) for post in pickle.loads(pickled_pinned)]

        # Get only needed chunks for current page
        chunk_count = cache.get('posts_chunk_count', 0)
        page = int(request.GET.get('page', 1))
        chunks_needed = min(3, max(1, page))  # Load 1-3 chunks based on page

        regular_posts = []
        # Load all chunks instead of just the first few
        for i in range(chunk_count):
            compressed_chunk = cache.get(f'posts_chunk_{i}')
            if compressed_chunk:
                try:
                    chunk = pickle.loads(lz4.decompress(compressed_chunk))
                    regular_posts.extend(DictToObject(post) for post in chunk)
                except Exception as e:
                    logger.error(f"Error loading chunk {i}: {e}")
                    continue

        if pinned_posts or regular_posts:
            return {
                'posts': regular_posts,
                'pinned_posts': pinned_posts,
                'total_chunks': chunk_count
            }

        return get_optimized_posts()

    except Exception as e:
        logger.error(f"Cache error: {e}")
        return get_optimized_posts()

class DictToObject:
    """Convert dictionary to object-like structure with support for FileField URLs"""
    def __init__(self, data):
        for key, value in data.items():
            if key in ['media_file', 'image']:
                # Create a FileField-like object with a url attribute
                if value:
                    setattr(self, key, FileFieldLike(value))
                else:
                    setattr(self, key, None)
            else:
                setattr(self, key, value)
    
    def get_item_type(self):
        return "Post"

class FileFieldLike:
    """Mimics Django's FileField with url attribute"""
    def __init__(self, url):
        if url and not url.startswith(settings.MEDIA_URL):  # Ensure MEDIA_URL is prefixed
            self.name = url.split('/')[-1] 
            self.url = f"{settings.MEDIA_URL}{url.lstrip('/')}"
        else:
            self.url = url  # Already correctly formatted

def load_posts(request):
    # Check if this is a pagination request
    is_pagination = 'page' in request.GET
    
    # Only consider loading screen for non-pagination requests
    is_loading = not request.COOKIES.get('loading_complete', False) and not is_pagination
    
    current_route = resolve(request.path_info).url_name
    if current_route == 'post-detail':
        return {
            'days_since_launch': days_since_launch(),
            'comment_form': CommentForm(),
            'is_loading': is_loading,
        }
    elif current_route == 'stream-posts':
        return { 'is_loading': is_loading }

    # Try cache first, fallback to database
    posts_data = get_cached_posts(request)




    # Add comments context
    
 
    for post in posts_data['pinned_posts']:
        query_post = Post.objects.get(id=post.id)
        comments = Comment.objects.filter(post=query_post).order_by('-created_on')
        # Attach comments and total count directly to the post object
        post.comments_total = comments.count()
        post.recent_comments = comments

    
    highlight_comments = Comment.objects.all().order_by('-created_on')[:5]

    all_comments = Comment.objects.all().order_by('-created_on').filter(spam_score__lt=50)

    # Combine posts and comments into a single feed
    combined_items = sorted(
        chain(posts_data['posts'], all_comments),
        key=lambda x: x.date_posted if hasattr(x, 'date_posted') else x.created_on,
        reverse=True
    )

    # Paginate the combined feed items
    items_per_page = 50
    paginator = Paginator(combined_items, items_per_page) 
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Process each item in the page and STORE THE RESULTS back in the object list
    processed_items = []
    for item in page_obj.object_list:
        if hasattr(item, 'get_item_type') and item.get_item_type() == 'Post':
            processed_items.append(preprocess_post(item))
        else:
            processed_items.append(preprocess_comment(item))
    
    # Replace the items in the page with the processed ones
    page_obj.object_list = processed_items
    
    return {
        'days_since_launch': days_since_launch(),
        'comment_form': CommentForm(),
        'search_form': PostSearchForm(), 
        'postForm': PostForm(),
        'posts': page_obj,
        'pinned_posts': posts_data['pinned_posts'],
        'spite': Post.objects.count() + Comment.objects.count(),
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
        posts = Post.objects.filter(is_pinned=False).filter(spam_score__lt=50).order_by('-date_posted')

        logger.info(f"Fetched {pinned_posts.count()} pinned posts and {posts.count()} unpinned posts from the database.")
        posts_data = {'posts': posts, 'pinned_posts': pinned_posts}  # Fallback data
    else:
        # Load the cached posts data
        logger.info("Loaded posts from cache.")
        posts_data = pickle.loads(zlib.decompress(compressed_posts_data))

        posts = posts_data['posts']
        pinned_posts = posts_data['pinned_posts']
    return posts_data, posts, pinned_posts

def get_paginated_posts(page_number=1):
    """Consistent pagination across all views"""
    posts_data = get_optimized_posts()
    
    # Create paginator from cached data
    paginator = Paginator(posts_data['posts'], 20)
    
    try:
        current_page = paginator.page(page_number)
    except (EmptyPage):
        current_page = paginator.page(1)
    
    return {
        'posts': current_page,
        'pinned_posts': posts_data['pinned_posts'],
        'has_more': current_page.has_next(),
        'current_page': page_number,
        'total_pages': paginator.num_pages
    }

