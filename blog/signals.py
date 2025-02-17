from django.db.models.signals import post_save, post_delete
from asgiref.sync import async_to_sync
from django.contrib.sessions.models import Session
from spite.tasks import cache_posts_data
from django.dispatch import receiver
import logging 
from django.core.cache import cache
from django.utils.timezone import localtime
from .models import Post, Comment, BlockedIP
from django.conf import settings 
import requests
from django.core.serializers.json import DjangoJSONEncoder
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json
from spite.tasks import summarize_posts
from channels.exceptions import ChannelFull
from redis.exceptions import ConnectionError

logger = logging.getLogger('spite')

@receiver(post_save, sender=Post)
def clear_cache_on_post_save(sender, instance, created, **kwargs):
    """Ensure all cache keys are cleared consistently"""
    logger.info(f"Post {instance.id} saved. Clearing post caches")
    
    # Clear all post-related caches
    cache.delete('pinned_posts')
    cache.delete('posts_data')
    for i in range(cache.get('posts_chunk_count', 0)):
        cache.delete(f'posts_chunk_{i}')
    cache.delete('posts_chunk_count')
    
    # Trigger async cache rebuild
    cache_posts_data.delay()
    
    # Return immediately to not block post creation
    logger.info(f"Post caches cleared and rebuild triggered")


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

@receiver(post_save, sender=Post)
def broadcast_new_post(sender, instance, created, **kwargs):
    if created:  # Only broadcast new posts
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "posts",  # Group name for clients subscribed to post updates
                {
                    "type": "post_message",
                    "message": {
                        "id": instance.id,
                        "title": instance.title,
                        "content": instance.content,
                        'date_posted': localtime(instance.date_posted).strftime('%b. %d, %Y, %I:%M %p'),
                        "anon_uuid": str(instance.anon_uuid),
                        "parent_post": {
                            "id": instance.parent_post.id,
                            "title": instance.parent_post.title,
                        } if instance.parent_post else None,
                        "city": instance.city,
                        "contact": instance.contact,
                        "media_file": {"url": instance.media_file.url} if instance.media_file else None,
                        "image": instance.image.url if instance.image else None,
                        "is_image": instance.is_image,
                        "is_video": instance.is_video,
                        "display_name": instance.display_name,
                    },
                },
            )
        except (ConnectionError, ChannelFull):
            logger.error("Failed to send post message to channel layer")
            #Continue wo broadcasting
            pass

@receiver(post_save, sender=Comment)
def broadcast_new_comment(sender, instance, created, **kwargs):
    if created:
        channel_layer = get_channel_layer()
        message = {
            "id": instance.id,
            "post_id": instance.post.id,
            "post_title": instance.post.title, 
            "content": instance.content,
            "name": instance.name,
            "created_on": localtime(instance.created_on).strftime('%b. %d, %Y, %I:%M %p'),
        }
        logger.info(message)

        # Validate JSON
        try:
            json.dumps(message, cls=DjangoJSONEncoder)  # Ensure serializability
            async_to_sync(channel_layer.group_send)(
                "comments", 
                {"type": "comment_message", "message": message}
            )
        except TypeError as e:
            print(f"JSON serialization error: {e}")


# @receiver(post_save, sender=Post)
def trigger_summary(sender, instance, **kwargs):
    post_count = Post.objects.count()
    if post_count % 100 == 0:  # Trigger after every 100th post
        summarize_posts.delay()
    

@receiver([post_save, post_delete], sender=BlockedIP)
def clear_blocked_ips_cache(sender, **kwargs):
    cache.delete('blocked_ips')