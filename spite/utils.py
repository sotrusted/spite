from django.core.cache import cache
from functools import wraps
import pylibmc
import logging

logger = logging.getLogger(__name__)

def cache_large_data(key, timeout=900):  # 15 minutes default
    """
    Decorator to handle large cached items
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate data
            data = func(*args, **kwargs)

            # Skip caching if data is None (error case)
            if data is None:
                return data

            # Try to cache the data, but don't fail if it's too big
            try:
                cache.set(key, data, timeout)
            except (pylibmc.TooBig, Exception) as e:
                logger.debug(f"Could not cache large data for key {key}: {str(e)}")
                # Continue execution even if caching fails
                pass

            return data
        return wrapper
    return decorator 

import base64

def get_image_as_base64(path):
    with open(path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
        return encoded_string.decode('utf-8')


from django.template.loader import render_to_string
from django.template import Context

def render_post_fragment(post, comment_form=None):
    """Render a single post as HTML fragment"""
    context = {
        'post': post,
        'comment_form': comment_form or CommentForm(),
        'nested': False,
    }
    return render_to_string('blog/partials/post.html', context)

def render_comment_fragment(comment, comment_form=None):
    """Render a single comment as HTML fragment"""
    context = {
        'comment': comment,
        'comment_form': comment_form or CommentForm(),
    }
    return render_to_string('blog/partials/comment.html', context)