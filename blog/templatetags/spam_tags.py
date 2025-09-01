from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def spam_indicator(post):
    """Display spam indicator for posts"""
    if hasattr(post, 'spam_score') and post.spam_score > 0:
        if post.spam_score >= 50:
            return mark_safe('<span class="badge badge-danger">Hidden (High Spam)</span>')
        elif post.spam_score >= 30:
            return mark_safe('<span class="badge badge-warning">Pushed Down (Medium Spam)</span>')
        else:
            return mark_safe('<span class="badge badge-info">Low Spam Risk</span>')
    return ''

@register.filter
def spam_score_display(post):
    """Display spam score for posts"""
    if hasattr(post, 'spam_score') and post.spam_score > 0:
        return f"Spam Score: {post.spam_score}"
    return ""

@register.filter
def spam_reasons_display(post):
    """Display spam reasons for posts"""
    if hasattr(post, 'spam_reasons') and post.spam_reasons:
        return f"Reasons: {post.spam_reasons}"
    return "" 