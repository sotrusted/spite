import pickle
import zlib
from celery import shared_task
from django.core.cache import cache
from blog.models import Post
from django.db.models import Q
import logging

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
        compressed_posts_data = zlib.compress(pickle.dumps(posts_data))

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
                logger.warning(f"Failed to cache HTML for {view_name} page {pavge_number}. Status code: {response.status_code}")

    except Exception as e:
        logger.error(f"Error caching HTML for {view_name} page {page_number}: {e}")
    return True



@shared_task
def test_task():
    print("Test task executed!")
    return "Test task completed!"
