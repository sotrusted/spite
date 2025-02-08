import pickle
import datetime
import lz4.frame as lz4
import zlib
from celery import shared_task
from django.core.cache import cache
from blog.models import Post, Summary
from .openai import generate_summary
from django.db.models import Q
import logging
from blog.models import PageView
from spite.utils import cache_large_data

# Get the 'spite' logger
logger = logging.getLogger('spite')

def process_post(post):
    post_data = {
        'id': post.id,
        'title': post.title,
        'content': post.content,
        'display_name': post.display_name,
        'date_posted': post.date_posted,
        'is_image': post.is_image(),
        'is_video': post.is_video(),
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

@shared_task
def cache_posts_data():
    try:
        # Use iterator and values_list for minimal memory usage
        base_query = Post.objects.values_list(
            'id', 'title', 'content', 'display_name',
            'date_posted', 'is_pinned', 'media_file', 'image',
            'parent_post', 'anon_uuid'
        ).iterator(chunk_size=50)  # Smaller chunk size

        pinned_posts = []
        chunk_count = 0
        current_chunk = []
        
        for post in base_query:
            post_dict = {
                'id': post[0],
                'title': post[1],
                'content': post[2],
                'display_name': post[3],
                'date_posted': post[4],
                'is_pinned': post[5],
                'media_file': {'url': post[6]} if post[6] else None,
                'image': {'url': post[7]} if post[7] else None,
                'parent_post': post[8],
                'anon_uuid': post[9],
            }
            
            if post_dict['is_pinned']:
                pinned_posts.append(post_dict)
            else:
                current_chunk.append(post_dict)
                if len(current_chunk) >= 50:  # Smaller chunks
                    compressed = lz4.compress(pickle.dumps(current_chunk))
                    cache.set(f'posts_chunk_{chunk_count}', compressed, timeout=300)  # 5 min timeout
                    chunk_count += 1
                    current_chunk = []
                    
        # Handle remaining posts
        if current_chunk:
            compressed = lz4.compress(pickle.dumps(current_chunk))
            cache.set(f'posts_chunk_{chunk_count}', compressed, timeout=300)
            chunk_count += 1

        # Cache pinned posts
        if pinned_posts:
            compressed_pinned = lz4.compress(pickle.dumps(pinned_posts))
            cache.set('pinned_posts', compressed_pinned, timeout=300)
            
        cache.set('posts_chunk_count', chunk_count, timeout=300)
        logger.info(f"Cached {len(pinned_posts)} pinned posts and {chunk_count} chunks")

    except Exception as e:
        logger.error(f"Error caching posts: {e}", exc_info=True)

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