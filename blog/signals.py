from django.db.models.signals import post_save
from spite.tasks import cache_posts_data
from django.dispatch import receiver
import logging 
from django.core.cache import cache
from .models import Post, Comment
from django.conf import settings 
import requests

logger = logging.getLogger('spite')

@receiver(post_save, sender=Post)
def clear_cache_on_post_save(sender, instance, **kwargs):
    logger.info(f"Post {instance.id} saved. Clearing cache")
    
    #Cache posts 
    cache.clear()
    logger.info(f"Cache cleared")


@receiver(post_save, sender=Comment)
def clear_comments_cache(sender, instance, created, **kwargs):
    """
    Clears the cached comments data when a new Comment is saved.
    """
    logger.info(f"Comment {instance.id} saved. Clearing cache")
    if created:
        cache.clear()
    logger.info(f"Cache cleared")


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
        logger.info(response.json())


@receiver(post_save, sender=Comment)
def refresh_recent_comments(sender, instance, created, **kwargs):
    """
    Signal to refresh recent_comments on the related Post
    when a new Comment is saved.
    """
    if created:  # Only run when a new comment is created
        post = instance.post
        # Refresh recent_comments for the post
        comments = Comment.objects.filter(post=post).order_by('-created_on')
        post.recent_comments = comments[:5]  # Update recent_comments attribute
        # Optionally log for debugging
        print(f"Updated recent comments for Post ID {post.id}")