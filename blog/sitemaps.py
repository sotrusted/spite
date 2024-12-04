from django.contrib.sitemaps import Sitemap
from .models import Post  # Import Post model 
from django.shortcuts import reverse


class PostSitemap(Sitemap):
    changefreq = "weekly"  # Indicates how frequently the content changes
    priority = 0.8  # Priority (0.0 - 1.0) relative to other URLs in the sitemap

    def items(self):
        return Post.objects.all().order_by('-date_posted') # Queryset of items to include

    def lastmod(self, obj):
        return obj.date_posted  # Use the model's last updated timestamp


class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = 'yearly'

    def items(self):
        return ['home', 'shop']  # List of named URL patterns

    def location(self, item):
        return reverse(item)