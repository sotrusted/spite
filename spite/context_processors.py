from blog.models import Post
from django.core.paginator import Paginator
from django.conf import settings 
import os
from spite.count_users import count_ips
from django.contrib.sessions.models import Session

from datetime import datetime, timezone


def load_posts(request):
    posts = Post.objects.filter(is_pinned=False).order_by('-date_posted')

    pinned_posts = Post.objects.filter(is_pinned=True)

    paginator = Paginator(posts, 200) # Number to load initially
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    iplog = os.path.join(settings.BASE_DIR, 'iplog')
    user_count = count_ips(iplog)

    current_time = datetime.now(timezone.utc)
    current_date = current_time.date()
    daily_user_count = count_ips(iplog, date=current_date)

    active_sessions_count = getattr(settings, 'ACTIVE_SESSION_COUNT', 0)

    return {
        'days_since_launch' : days_since_launch(),
        'posts': page_obj,
        'pinned_posts' : pinned_posts, 
        'spite' : len(posts),
        'user_count' : user_count,
        'daily_user_count' : daily_user_count,
        'active_sessions_count' : active_sessions_count,  
        'is_paginated' : page_obj.has_other_pages(), 
    }

def days_since_launch():
    site_launch_date = datetime(2024, 8, 23)
    current_date = datetime.now()
    days_since = (current_date - site_launch_date).days
    return days_since
