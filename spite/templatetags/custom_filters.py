from django import template
from django.utils.text import Truncator
from django.utils.safestring import mark_safe
import re

register = template.Library()

@register.filter
def truncate_and_preserve_linebreaks(value, arg):
    truncated_text = Truncator(value).words(arg, truncate='...', html=True)
    return mark_safe(truncated_text)


@register.filter
def multiply(value, arg):
    return value * arg