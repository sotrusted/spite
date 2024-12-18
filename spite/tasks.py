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

# Get the 'spite' logger
logger = logging.getLogger('spite')

@shared_task
def cache_posts_data():
    try:
        # Fetch all posts in a single query
        all_posts = Post.objects.filter(Q(is_pinned=True) | Q(is_pinned=False)).order_by('-date_posted')

        # Separate the pinned and unpinned posts in Python
        pinned_posts = [post for post in all_posts if post.is_pinned]
        posts = [post for post in all_posts if not post.is_pinned]

        # Compress and cache the posts data
        posts_data = {'posts': posts, 'pinned_posts': pinned_posts}

        # compressed_posts_data = zlib.compress(pickle.dumps(posts_data))
        # Serialize with pickle
        pickled_data = pickle.dumps(posts_data)

        # Compress the pickled data with LZ4
        compressed_posts_data = lz4.compress(pickled_data)


        # Cache the compressed data
        cache.set('posts_data', compressed_posts_data, 60 * 15)

        # Log the success
        logger.info(f"Posts data successfully cached with {len(posts)} unpinned posts and {len(pinned_posts)} pinned posts.")
    except Exception as e:
        logger.error(f"Error caching posts data: {e}")
    return True

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
    posts = Post.objects.order_by('-id')[:100]


    logger.info(f'Summarizing 100 posts ending at post number {count}')

    # Compile post content
    content = 'Posts: '
    for post in posts:
        try:
            content += '\n' + post.print_long()
        except Exception as e:
            logger.error(f"Error processing post {post.id}: {e}")
    content = content[:29500]

    logger.info(f'Content: {content}')
    
    # Fetch previous summaries to add memory
    previous_summaries = Summary.objects.all().order_by('-id')[:5]  # Limit to the last 5 summaries

    memory = ''
    for summary in previous_summaries:
        memory += ' ' + f'{summary.title}-{summary.summary}' 

    logger.info(f'Memory: {memory}')

    # Create a prompt for OpenAI
    summary_prompt = (
        f"Summarize the following forum posts. Include key points and themes. "
        f"Previous context: {memory}\n\nPosts:\n{content}"
    )
    
    # Generate summary using OpenAI
    summary_text = generate_summary(summary_prompt)


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
    # Fetch and reset the temporary pageview count
    temp_count = cache.get('pageview_temp_count', 0)
    if temp_count > 0:
        # Reset cache
        cache.set('pageview_temp_count', 0)

        # Persist to database
        pageview, _ = PageView.objects.get_or_create(id=1)
        pageview.count += temp_count
        pageview.save()