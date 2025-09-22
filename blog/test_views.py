from django.shortcuts import render
from django.core.cache import cache
from .models import Post
from django.http import HttpResponse
from blog.views import simple_password_required, get_client_ip
from django.core.cache import cache
from .models import List
from .models import SiteNotification
@simple_password_required
def editor(request):
    if request.method == "POST":
        content = request.POST.get("content", "")
        return HttpResponse(f"<h2>Submitted Content:</h2><div>{content}</div>")

    return render(request, "test/editor.html")

@simple_password_required
def sandbox(request):
    # Replicate the home view logic exactly, but add test=True
    
    # Get the immediate total count
    total_pageviews = cache.get('current_total_views', 0)

    # Cache the IP submission status for each IP
    client_ip = get_client_ip(request)
    cache_key = f'ip_submitted_{client_ip}'
    
    ip_has_submitted = cache.get(cache_key)
    if ip_has_submitted is None:
        # Only hit the database if not in cache
        ip_has_submitted = List.objects.filter(ip_address=client_ip).exists()
        # Cache for 7 hours (25200 seconds) - longer cache for better performance
        cache.set(cache_key, ip_has_submitted, 60 * 60 * 7)

    # Same context as home view, but with test=True added
    context = {
        'pageview_count': total_pageviews,
        'ip_has_submitted': ip_has_submitted,
        'test': True,  # This enables test features!
    }

    notifications = cache.get('notifications')
    if notifications is None:
        notifications = SiteNotification.objects.filter(timestamp__gte=timezone.now() - timedelta(days=7))
        cache.set('notifications', notifications, 60 * 60 * 24)
    notifications = SiteNotification.objects.all()
    context['notifications'] = notifications
    return render(request, 'blog/home.html', context)