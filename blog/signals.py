from django.db.models.signals import post_save
from spite.tasks import cache_posts_data
from django.dispatch import receiver
import logging 
from django.core.cache import cache
from .models import Post
from django.conf import settings 
import requests

logger = logging.getLogger('spite')

@receiver(post_save, sender=Post)
def clear_cache_on_post_save(sender, instance, **kwargs):
    logger.debug(f"Post {instance.id} saved. Clearing cache")
    
    #Cache posts 
    cache.clear()


@receiver(post_save, sender=Post)
def send_push_notification(sender, instance, created, **kwargs):
    if created:
        url = "https://api.pushover.net/1/messages.json"
        data = {
            "token": settings.PUSHOVER_API_TOKEN,
            "user": settings.PUSHOVER_USER_KEY,
            "message": f"A new post titled '{instance.title}' has been created.",
            "title": "New Post Created",
        }
        response = requests.post(url, data=data)
        logger.debug(response.json())