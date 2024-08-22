import uuid
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.urls import reverse
from django.template.defaultfilters import slugify
from django.db import models
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify

# Create your models here.
class Post(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True) 
    anon_uuid = models.UUIDField(default=uuid.uuid4, editable=False)

    title = models.CharField(max_length=100, verbose_name='What\'s your problem?')
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name='city or neighborhood')
    content = models.TextField(max_length=400, verbose_name='description', default='')
    contact = models.TextField(blank=True, null=True, verbose_name='contact info')
    image = models.ImageField(blank=True, null=True, verbose_name=f'image', upload_to='images/')
    date_posted = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('post-detail', kwargs={'pk' : self.pk})

    def save(self, *args, **kwargs):
        if not self.author:
            self.anonymous_uuid = uuid.uuid4()
        super.save(*args, **kwargs)


def get_image_filename(instance, filename):
    title = instance.personal.title
    slug = slugify(title)
    return "uploads/%s-%s" % (slug, filename)

"""
class Images(models.Model):
    personal = models.ForeignKey(Personal, default=None, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to=get_image_filename,
                              verbose_name="Image")
"""