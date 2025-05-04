from django.db import models
from django.utils.text import slugify

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class Artwork(models.Model):
    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to='artworks/')
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='artworks')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        self.slug = slugify(self.category.name + "-" + self.title + "-" + self.created_at.strftime("%Y%m%d%H%M%S"))
        super().save(*args, **kwargs)

class Bio(models.Model):
    content = models.TextField()
    last_updated = models.DateTimeField(auto_now=True)