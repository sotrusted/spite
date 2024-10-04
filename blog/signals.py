from django.db.models.signals import post_save
from spite.tasks import cache_posts_data
from django.dispatch import receiver
import logging 
from django.core.cache import cache
from .models import Post

logger = logging.getLogger('spite')

@receiver(post_save, sender=Post)
def clear_cache_on_post_save(sender, instance, **kwargs):
    logger.debug(f"Post {instance.id} saved. Clearing cache")
    
    #Cache posts 
    cache.clear()

