import pickle
import zlib
from django.core.cache import cache
from .tasks import cache_posts_data
from datetime import datetime, timedelta, timezone
import os

def posts_context(request):
    # Try to get posts from the cache
    compressed_posts_data = cache.get('posts_data')
    if not compressed_posts_data:
        # If no cached data, trigger Celery task to cache posts data
        cache_posts_data.delay()
        posts_data = {'posts': [], 'pinned_posts': []}  # Empty data as a fallback
    else:
        # Load the cached posts data
        posts_data = pickle.loads(zlib.decompress(compressed_posts_data))

    paginator = Paginator(posts_data['posts'], 20)  # Number to load initially
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get or calculate user count data
    user_count_data = cache.get('user_count_data')
    if not user_count_data:
        iplog = os.path.join(settings.BASE_DIR, 'iplog')
        current_time = datetime.now(timezone.utc)

        user_count, daily_user_count, active_sessions_count = \
            [count_ips(iplog, past_time=time) for time in \
             [None, current_time - timedelta(hours=24), current_time - timedelta(hours=1)]]

        user_count_data = {
            'user_count': user_count,
            'daily_user_count': daily_user_count,
            'active_sessions_count': active_sessions_count
        }

        cache.set('user_count_data', user_count_data, 60 * 1)

    return {
        'days_since_launch': days_since_launch(),
        'posts': page_obj,
        'pinned_posts': posts_data['pinned_posts'],
        'spite': len(posts_data['posts']),
        'user_count': user_count_data['user_count'],
        'daily_user_count': user_count_data['daily_user_count'],
        'active_sessions_count': user_count_data['active_sessions_count'],
        'is_paginated': page_obj.has_other_pages(),
    }

def days_since_launch():
    site_launch_date = datetime(2024, 8, 23)
    current_date = datetime.now()
    days_since = (current_date - site_launch_date).days
    return days_since
