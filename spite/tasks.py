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

@shared_task
@cache_large_data(key='full_posts_data', timeout=60 * 15)  # 15 minutes
def cache_posts_data():
    try:
        # Get posts with optimized query
        base_query = Post.objects.only(
            'id', 'title', 'content', 'display_name',
            'date_posted', 'is_pinned', 'media_file', 'image'
        ).order_by('-date_posted')

        # Process all posts
        all_posts = list(base_query)
        pinned_posts = [post for post in all_posts if post.is_pinned]
        regular_posts = [post for post in all_posts if not post.is_pinned]

        logger.info(f"Caching {len(all_posts)} posts")

        # Cache pinned posts
        compressed_pinned = lz4.compress(pickle.dumps(pinned_posts))
        cache.set('pinned_posts', compressed_pinned)

        # Split regular posts into chunks of 1000
        chunk_size = 1000
        chunks = [regular_posts[i:i + chunk_size] for i in range(0, len(regular_posts), chunk_size)]
        
        # Cache each chunk separately
        for i, chunk in enumerate(chunks):
            compressed_chunk = lz4.compress(pickle.dumps(chunk))
            cache.set(f'posts_chunk_{i}', compressed_chunk)
        
        # Store the number of chunks
        cache.set('posts_chunk_count', len(chunks))

        logger.info(f"Successfully cached {len(pinned_posts)} pinned posts and {len(chunks)} chunks of regular posts")
        
        return {
            'pinned_posts': pinned_posts,
            'regular_posts': regular_posts
        }
        
    except Exception as e:
        logger.error(f"Error caching posts data: {str(e)}", exc_info=True)
        return None

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