from django.db.models.signals import post_save
from django.dispatch import receiver
import logging 
from django.core.cache import cache
from .models import Post

logger = logging.getLogger('spite')

@receiver(post_save, sender=Post)
def clear_cache_on_post_save(sender, instance, **kwargs):
    logger.debug(f"Post {instance.id} saved. Clearing cache")
    # Clear the cache when a new post is saved
    cache.clear()
    
