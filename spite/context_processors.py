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

def preprocess_posts_for_template(items):
    """Preprocess posts and comments to avoid expensive template operations"""
    for item in items:
        # Handle both Posts and Comments
        if hasattr(item, 'get_item_type'):
            if item.get_item_type == 'Post':
                # Pre-calculate formatted date for posts
                if hasattr(item, 'date_posted') and item.date_posted:
                    item.formatted_date = item.date_posted.strftime('%B %d, %Y, %I:%M %p')
                
                # Pre-calculate excerpt for posts
                if hasattr(item, 'content') and item.content:
                    item.excerpt = create_excerpt(item.content)
                    
            elif item.get_item_type == 'Comment':
                # Pre-calculate formatted date for comments
                if hasattr(item, 'created_on') and item.created_on:
                    item.formatted_date = item.created_on.strftime('%B %d, %Y, %I:%M %p')
                
                # Pre-calculate excerpt for comments
                if hasattr(item, 'content') and item.content:
                    item.excerpt = create_excerpt(item.content)
        else:
            # Fallback for items without get_item_type (shouldn't happen but be safe)
            if hasattr(item, 'date_posted') and item.date_posted:
                item.formatted_date = item.date_posted.strftime('%B %d, %Y, %I:%M %p')
            elif hasattr(item, 'created_on') and item.created_on:
                item.formatted_date = item.created_on.strftime('%B %d, %Y, %I:%M %p')
            
            if hasattr(item, 'content') and item.content:
                item.excerpt = create_excerpt(item.content)
    
    return items

def create_excerpt(content):
    """Create excerpt with proper line break handling"""
    if not content:
        return ""
        
    content = content.strip()
    
    # Handle line breaks properly - split by lines first
    lines = content.split('\n')
    excerpt_lines = []
    total_chars = 0
    
    for line in lines:
        line = line.strip()
        if not line:  # Skip empty lines
            continue
            
        if total_chars + len(line) > 200:
            # If adding this line would exceed 200 chars, truncate it
            remaining_chars = 200 - total_chars
            if remaining_chars > 3:  # Only add if we have space for "..."
                excerpt_lines.append(line[:remaining_chars-3] + '...')
            break
        else:
            excerpt_lines.append(line)
            total_chars += len(line)
            
            # Limit to 3 lines max
            if len(excerpt_lines) >= 3:
                break
    
    return '\n'.join(excerpt_lines)

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
        
        # If cache is older than 10 minutes, trigger async refresh (non-blocking)
        # Use a longer threshold to prevent constant refreshes
        if not last_update or (current_time - last_update) > 600:  # 10 minutes
            logger.info("Cache stale or missing, triggering async refresh")
            cache_posts_data.delay()  # Async call - non-blocking
            
        # OPTIMIZED: Get pinned posts (usually few)
        compressed_pinned = cache.get('pinned_posts')
        pinned_posts = []
        if compressed_pinned:
            try:
                pickled_pinned = lz4.decompress(compressed_pinned)
                pinned_posts = [DictToObject(post) for post in pickle.loads(pickled_pinned)]
            except Exception as e:
                logger.error(f"Error loading pinned posts: {e}")

        # OPTIMIZED: Load chunks more efficiently
        chunk_count = cache.get('posts_chunk_count', 0)
        regular_posts = []
        
        # Load all chunks but with better error handling
        for i in range(chunk_count):
            compressed_chunk = cache.get(f'posts_chunk_{i}')
            if compressed_chunk:
                try:
                    chunk = pickle.loads(lz4.decompress(compressed_chunk))
                    chunk_posts = [DictToObject(post) for post in chunk]
                    # Add get_item_type attribute to each post for template compatibility
                    for post in chunk_posts:
                        post.get_item_type = "Post"
                    regular_posts.extend(chunk_posts)
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

def get_cached_comments():
    """Get comments from cache, fallback to database if needed"""
    try:
        comment_chunk_count = cache.get('comments_chunk_count', 0)
        all_comments = []
        
        # Load all comment chunks from cache
        for i in range(comment_chunk_count):
            compressed_chunk = cache.get(f'comments_chunk_{i}')
            if compressed_chunk:
                try:
                    chunk = pickle.loads(lz4.decompress(compressed_chunk))
                    # Convert dict to Comment-like objects
                    comment_objects = []
                    for comment_data in chunk:
                        comment_obj = CommentDictToObject(comment_data)
                        comment_objects.append(comment_obj)
                    all_comments.extend(comment_objects)
                except Exception as e:
                    logger.error(f"Error loading comment chunk {i}: {e}")
                    continue
        
        if all_comments:
            return all_comments
        
        # Fallback to database if cache is empty
        logger.info("Comment cache empty, fetching from database")
        return Comment.objects.select_related('post', 'parent_comment').filter(
            spam_score__lt=50
        ).order_by('-created_on')
        
    except Exception as e:
        logger.error(f"Error in get_cached_comments: {e}")
            # Fallback to database
    comments = Comment.objects.select_related('post').filter(
        spam_score__lt=50
    ).order_by('-created_on')
    
    # Add get_item_type attribute to each comment for template compatibility
    for comment in comments:
        comment.get_item_type = "Comment"
    
    return comments

class CommentDictToObject:
    """Convert comment dictionary to object-like structure with related objects"""
    def __init__(self, data):
        # Set basic comment fields
        for key, value in data.items():
            if key == 'media_file':
                # Create a FileField-like object with a url attribute
                if value:
                    setattr(self, key, FileFieldLike(value))
                else:
                    setattr(self, key, None)
            elif not key.startswith('post__') and not key.startswith('parent_comment__'):
                setattr(self, key, value)
        
        # Add get_item_type attribute for template compatibility
        self.get_item_type = "Comment"
        
        # Create post object if post data exists
        if any(key.startswith('post__') for key in data.keys()):
            post_data = {}
            for key, value in data.items():
                if key.startswith('post__'):
                    field_name = key.replace('post__', '')
                    if field_name in ['media_file', 'image']:
                        if value:
                            post_data[field_name] = FileFieldLike(value)
                        else:
                            post_data[field_name] = None
                    else:
                        post_data[field_name] = value
            
            self.post = DictToObject(post_data)
        else:
            self.post = None
        
        # Create parent comment object if parent comment data exists
        if any(key.startswith('parent_comment__') for key in data.keys()):
            parent_data = {}
            for key, value in data.items():
                if key.startswith('parent_comment__'):
                    field_name = key.replace('parent_comment__', '')
                    if field_name == 'media_file':
                        if value:
                            parent_data[field_name] = FileFieldLike(value)
                        else:
                            parent_data[field_name] = None
                    else:
                        parent_data[field_name] = value
            
            self.parent_comment = CommentDictToObject(parent_data)
        else:
            self.parent_comment = None

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
        
        # Add get_item_type attribute for template compatibility
        self.get_item_type = "Post"

class FileFieldLike:
    """Mimics Django's FileField with url attribute"""
    def __init__(self, url):
        if url and isinstance(url, str) and not url.startswith(settings.MEDIA_URL):  # Ensure MEDIA_URL is prefixed
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
    elif current_route in ['admin', 'static', 'api']:
        return {}



    # Try cache first, fallback to database
    posts_data = get_cached_posts(request)

    # OPTIMIZED: Use cached comments for pinned posts to avoid database queries
    if posts_data['pinned_posts']:
        # Get cached comments data for pinned posts
        cached_pinned_comments = cache.get('pinned_comments_data')
        if cached_pinned_comments:
            try:
                import json
                comments_data = json.loads(cached_pinned_comments)
                # Attach cached comments to pinned posts
                for post in posts_data['pinned_posts']:
                    post_comments = comments_data.get(str(post.id), [])
                    post.comments_total = len(post_comments)
                    post.recent_comments = post_comments[:5]
            except Exception as e:
                logger.error(f"Error loading cached pinned comments: {e}")
                # Fallback to database query only if cache fails
                pinned_post_ids = [post.id for post in posts_data['pinned_posts']]
                pinned_comments = Comment.objects.filter(
                    post_id__in=pinned_post_ids
                ).select_related('post').order_by('-created_on')
                
                # Group comments by post_id
                comments_by_pinned_post = {}
                for comment in pinned_comments:
                    if comment.post_id not in comments_by_pinned_post:
                        comments_by_pinned_post[comment.post_id] = []
                    comments_by_pinned_post[comment.post_id].append(comment)
                
                # Attach comments to pinned posts
                for post in posts_data['pinned_posts']:
                    post.comments_total = len(comments_by_pinned_post.get(post.id, []))
                    post.recent_comments = comments_by_pinned_post.get(post.id, [])[:5]

    # OPTIMIZED: Use cached highlight comments (kept for future use)
    highlight_comments = cache.get('highlight_comments')
    if not highlight_comments:
        highlight_comments = list(Comment.objects.select_related('post').filter(
            spam_score__lt=50
        ).order_by('-created_on')[:5])
        cache.set('highlight_comments', highlight_comments, 300)  # Cache for 5 minutes

    # Load ALL comments as quote posts from cache
    all_comments = get_cached_comments()
    
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

    # Optimize item processing - batch load comments for posts in current page
    post_items = [item for item in page_obj.object_list if hasattr(item, 'get_item_type') and item.get_item_type == 'Post']
    comment_items = [item for item in page_obj.object_list if not (hasattr(item, 'get_item_type') and item.get_item_type == 'Post')]
    
    # Batch load comments for all posts in the page
    if post_items:
        post_ids = [item.id for item in post_items]
        comments_by_post = {}
        comments_queryset = Comment.objects.filter(
            post_id__in=post_ids
        ).order_by('-created_on').select_related('post', 'parent_comment')
        
        for comment in comments_queryset:
            if comment.post_id not in comments_by_post:
                comments_by_post[comment.post_id] = []
            comments_by_post[comment.post_id].append(comment)
        
        # Attach comments to posts
        for post in post_items:
            post.comments_total = len(comments_by_post.get(post.id, []))
            post.recent_comments = comments_by_post.get(post.id, [])[:5]
    
    # Process items (comments don't need additional processing)
    processed_items = list(chain(sorted(
        post_items + comment_items,
        key=lambda x: x.date_posted if hasattr(x, 'date_posted') else x.created_on,
        reverse=True
    )))
    
    # Replace the items in the page with the processed ones
    page_obj.object_list = processed_items
    
    # OPTIMIZED: Preprocess posts for template efficiency
    page_obj.object_list = preprocess_posts_for_template(page_obj.object_list)
    posts_data['pinned_posts'] = preprocess_posts_for_template(posts_data['pinned_posts'])
    
    return {
        'days_since_launch': days_since_launch(),
        'comment_form': CommentForm(),
        'search_form': PostSearchForm(), 
        'postForm': PostForm(),
        'posts': page_obj.object_list,  # Return the actual list of items, not the paginator
        'posts_has_next': page_obj.has_next(),  # Add separate has_next variable for infinite scroll
        'posts_next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
        'pinned_posts': posts_data['pinned_posts'],
        'spite': cache.get('total_posts_comments', 0),  # Cache this expensive query
        'is_paginated': page_obj.has_other_pages(),
        'highlight_comments': highlight_comments,
        'is_loading': is_loading,
        'htmx': True,  # Enable HTMX features in templates
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

