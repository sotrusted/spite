import pickle
import datetime
import lz4.frame as lz4
import zlib
from celery import shared_task
from django.core.cache import cache
from blog.models import Post, Summary, Comment
from .openai import generate_summary
from django.db.models import Q
import logging
from blog.models import PageView
from spite.utils import cache_large_data
from django.db.models import Prefetch
from functools import lru_cache

# Get the 'spite' logger
logger = logging.getLogger('spite')

def process_post(post):
    post_data = {
        'id': post.id,
        'title': post.title,
        'content': post.content,
        'display_name': post.display_name,
        'date_posted': post.date_posted,
        'is_image': post.is_image,
        'is_video': post.is_video,
        'anon_uuid': post.anon_uuid,
        'is_pinned': post.is_pinned,
        'media_file': {
            'url': post.media_file.url if post.media_file else None,
        } if post.media_file else None,
        'image': {
            'url': post.image.url if post.image else None,
        } if post.image else None,
        'like_count': post.like_count,
        'parent_post': post.parent_post,
        'ip_address': post.ip_address,
        'encrypted_ip': post.encrypted_ip,
    }
    return post_data

@shared_task
def process_post_chunk(posts_chunk):
    """Process a small chunk of posts to reduce memory usage"""
    return [process_post(post) for post in posts_chunk]

from spite.utils import render_post_fragment, render_comment_fragment

@shared_task
def cache_posts_data():
    """Cache posts with better memory management"""
    try:
        # Use values() for minimal memory usage - ADD SPAM FILTERING
        posts = Post.objects.values(
            'id',
            'title',
            'content',
            'display_name',
            'date_posted',
            'is_pinned',
            'media_file',
            'image',
            'anon_uuid',
            'parent_post', 
            'anon_uuid',
            'is_image',
            'is_video',
            'spam_score',  # Add spam_score to values
            'comment_count',
        ).filter(
            spam_score__lt=50  # FILTER OUT SPAM POSTS
        ).order_by('-date_posted')
        
        # Process in smaller chunks
        CHUNK_SIZE = 20
        chunks = []
        pinned_posts = []
        
        for post in posts:
            if post['is_pinned']:
                pinned_posts.append(post)
            else:
                if len(chunks) == 0 or len(chunks[-1]) >= CHUNK_SIZE:
                    chunks.append([])
                chunks[-1].append(post)
        
        # Cache with expiration
        CACHE_TIMEOUT = 300  # 5 minutes
        
        # Clear old chunks first
        old_chunk_count = cache.get('posts_chunk_count', 0)
        for i in range(old_chunk_count):
            cache.delete(f'posts_chunk_{i}')
        
        # Cache new chunks
        for i, chunk in enumerate(chunks):
            compressed = lz4.compress(pickle.dumps(chunk))
            cache.set(f'posts_chunk_{i}', compressed, CACHE_TIMEOUT)
        
        # Cache pinned posts and chunk count
        if pinned_posts:
            compressed_pinned = lz4.compress(pickle.dumps(pinned_posts))
            cache.set('pinned_posts', compressed_pinned, CACHE_TIMEOUT)
        
        cache.set('posts_chunk_count', len(chunks), CACHE_TIMEOUT)
        
        # Set the cache update timestamp so context processor knows cache is fresh
        from datetime import datetime
        cache.set('last_cache_update', datetime.now().timestamp(), CACHE_TIMEOUT)
        
        # OPTIMIZED: Cache comments as well since they're used as "quote posts"
        # Include related post data for proper rendering
        comments = Comment.objects.select_related('post', 'parent_comment').values(
            'id',
            'content',
            'name',
            'created_on',
            'post_id',
            'parent_comment_id',
            'media_file',
            'spam_score',
            # Include post data
            'post__id',
            'post__title',
            'post__content',
            'post__display_name',
            'post__date_posted',
            'post__media_file',
            'post__image',
            'post__is_image',
            'post__is_video',
            'post__anon_uuid',
            # Include parent comment data
            'parent_comment__id',
            'parent_comment__content',
            'parent_comment__name',
            'parent_comment__created_on',
            'parent_comment__media_file',
        ).filter(
            spam_score__lt=50
        ).order_by('-created_on')
        
        # Cache comments in chunks too
        comment_chunks = []
        for i in range(0, len(comments), CHUNK_SIZE):
            comment_chunk = list(comments[i:i + CHUNK_SIZE])
            comment_chunks.append(comment_chunk)
        
        # Cache comment chunks
        for i, comment_chunk in enumerate(comment_chunks):
            compressed_comments = lz4.compress(pickle.dumps(comment_chunk))
            cache.set(f'comments_chunk_{i}', compressed_comments, CACHE_TIMEOUT)
        
        cache.set('comments_chunk_count', len(comment_chunks), CACHE_TIMEOUT)
        
        # OPTIMIZED: Cache pinned comments data for faster loading
        if pinned_posts:
            pinned_comments_data = {}
            for post in pinned_posts:
                post_comments = Comment.objects.filter(
                    post_id=post['id']
                ).order_by('-created_on')[:5]  # Only get recent comments
                pinned_comments_data[str(post['id'])] = list(post_comments.values())
            
            import json
            cache.set('pinned_comments_data', json.dumps(pinned_comments_data), CACHE_TIMEOUT)
        
        # Cache the total count to avoid expensive queries on every request
        total_count = Post.objects.count() + Comment.objects.count()
        cache.set('total_posts_comments', total_count, CACHE_TIMEOUT)
        
        logger.info(f"Cached {len(pinned_posts)} pinned posts, {len(chunks)} post chunks, and {len(comment_chunks)} comment chunks (spam filtered)")
        
    except Exception as e:
        logger.error(f"Error in cache_posts_data: {e}")
        # Cleanup on error
        cache.delete('posts_chunk_count')
        cache.delete('pinned_posts')

@shared_task
def cache_page_html(view_name, page_number=None):
    from django.urls import reverse
    from django.test import Client

    try:
        # Use Django's test Client to render the page HTML
        client = Client()
        if page_number:
            url = reverse(view_name, kwargs={'page': page_number})
        else:
            url = reverse(view_name)
        response = client.get(url)

        if response.status_code == 200:
            # Cache the rendered HTML
            cache.set(f'{view_name}_html_page_{page_number}', response.content, 60 * 15)
            if response.status_code == 200:
                # Cache the rendered HTML
                cache.set(f'{view_name}_html_page_{page_number}', response.content, 60 * 15)
                logger.info(f"Cached HTML for {view_name} page {page_number} successfully.")
            else:
                logger.warning(f"Failed to cache HTML for {view_name} page {page_number}. Status code: {response.status_code}")

    except Exception as e:
        logger.error(f"Error caching HTML for {view_name} page {page_number}: {e}")
    return True

@shared_task
def test_task():
    print("Test task executed!")
    return "Test task completed!"

@shared_task
def summarize_posts():
    logger.info('Summarizing posts')
    # Fetch the latest 100 posts that haven't been summarized yet
    count = Post.objects.count()
    posts = Post.objects.order_by('-id')[:50]

    logger.info(f'Summarizing 50 posts ending at post number {count}')

    # Compile post content
    content = 'Posts: '
    for post in posts:
        try:
            content += '\n' + post.print_long()
            logger.info(len(content))
            if len(content) > 26000:
                break
        except Exception as e:
            logger.error(f"Error processing post {post.id}: {e}")

    # logger.info(f'Content: {content}')
    
    # Fetch previous summaries to add memory
    previous_summaries = Summary.objects.all().order_by('-id')[0]  # Limit to the last 5 summaries

    memory = ''
    for summary in previous_summaries:
        memory += ' ' + f'{summary.title}-{summary.summary}' 

    # logger.info(f'Memory: {memory}')

    # Create a prompt for OpenAI
    summary_prompt = (
        f"Give a take on the vibe of this online board from the perspective of a weary yet knowledgeable web surfer and 4chan troll trying to get girls to like him by being funny. "
        f"Previous context: {memory}\n\nPosts:\n{content}"
    )
    
    # Generate summary using OpenAI
    logger.info(f'Prompt length in chars: {len(summary_prompt)}')
    summary_text = generate_summary(summary_prompt,)

    title=f'eTips report, post {count}'

    # Save the summary
    Summary.objects.create(
        title=title,
        summary=summary_text,
    )

    Post.objects.create(
        title=title, 
        content=summary_text,
        display_name='eTips', 
    )

@shared_task
def persist_pageview_count():
    """
    Sync the pageview count from cache to the database.
    """
    try:
        # Fetch and reset the temporary pageview count
        temp_count = cache.get('pageview_temp_count', 0)
        if temp_count > 0:
            logger.info(f"Persisting {temp_count} pageviews to database")
            
            # Get or create the PageView object
            pageview, created = PageView.objects.get_or_create(id=1)
            
            # Update the count
            pageview.count += temp_count
            pageview.save()
            
            # Reset cache after successful persistence
            cache.set('pageview_temp_count', 0)
            
            logger.info(f"Successfully persisted pageviews. New total: {pageview.count}")
            
    except Exception as e:
        logger.error(f"Error persisting pageview count: {e}")

@shared_task
def cleanup_old_caches():
    # Clean up post chunks
    chunk_count = cache.get('posts_chunk_count', 0)
    for i in range(chunk_count):
        cache.delete(f'posts_chunk_{i}')
    cache.delete('posts_chunk_count')
    
    # Clean up comment chunks
    comment_chunk_count = cache.get('comments_chunk_count', 0)
    for i in range(comment_chunk_count):
        cache.delete(f'comments_chunk_{i}')
    cache.delete('comments_chunk_count')
    
    # Clean up other caches
    cache.delete('pinned_posts')
    cache.delete('highlight_comments')
    cache.delete('last_cache_update')
