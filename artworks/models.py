import uuid
from django.db import models
from django.utils.text import slugify
from django.urls import reverse

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
    is_featured = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0, db_index=True, blank=False, null=False)



    class Meta:
        ordering = ['-order']  # Changed to descending order

    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.category.name}-{self.title}-{str(uuid.uuid4())[:8]}")
        super().save(*args, **kwargs)    
    
    def get_absolute_url(self):
        return reverse('artwork_detail', kwargs={'slug': self.slug})

class Bio(models.Model):
    content = models.TextField()
    last_updated = models.DateTimeField(auto_now=True)