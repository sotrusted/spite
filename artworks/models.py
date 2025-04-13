from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class Artwork(models.Model):
    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to='artworks/')
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='artworks')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Bio(models.Model):
    content = models.TextField()
    last_updated = models.DateTimeField(auto_now=True)