from blog.models import Post
from django.conf import settings 
import os
from spite.count_users import count_ips
from django.contrib.sessions.models import Session

from datetime import datetime, timezone


def load_posts(request):
    posts = Post.objects.all().order_by('-date_posted')

    iplog = os.path.join(settings.BASE_DIR, 'iplog')
    user_count = count_ips(iplog)

    current_time = datetime.now(timezone.utc)
    active_sessions_count = Session.objects.filter(expire_date__gt=current_time).count()
    return {
        'days_since_launch' : days_since_launch(),
        'posts': posts,
        'spite' : len(posts),
        'user_count' : user_count,
        'active_sessions_count' : active_sessions_count,  
    }

def days_since_launch():
    site_launch_date = datetime(2024, 8, 23)
    current_date = datetime.now()
    days_since = (current_date - site_launch_date).days
    return days_since
