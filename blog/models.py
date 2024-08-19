from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.urls import reverse
from filer.fields.image import FilerImageField
from django.template.defaultfilters import slugify
from django.db import models
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify

# Create your models here.
class Personal(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True) 

    title = models.CharField(max_length=100, verbose_name='what are you looking for?')
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name='city or neighborhood')
    description = models.TextField(max_length=400, verbose_name='description', default='')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='phone')
    email = models.EmailField(blank=True, null=True, verbose_name='email')
    social_link = models.URLField(blank=True, null=True, verbose_name='social')
    image = models.ImageField(blank=True, null=True, verbose_name=f'image1', upload_to='images/')
    image1 = models.ImageField(blank=True, null=True, verbose_name=f'image1',  upload_to='images/')
    image2 = models.ImageField(blank=True, null=True, verbose_name=f'image2',  upload_to='images/')
    image3 = models.ImageField(blank=True, null=True, verbose_name=f'image3',  upload_to='images/')
    image4 = models.ImageField(blank=True, null=True, verbose_name=f'image4', upload_to='images/')
    image5 = models.ImageField(blank=True, null=True, verbose_name=f'image5',  upload_to='images/')
    image6 = models.ImageField(blank=True, null=True, verbose_name=f'image6',  upload_to='images/')
    date_posted = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('post-detail', kwargs={'pk' : self.pk})

    def get_images(self):
        image_fields = [self.image1, self.image2, self.image3, self.image4, self.image5, self.image6]
        images = [image for image in image_fields if image]
        return images

def get_image_filename(instance, filename):
    title = instance.personal.title
    slug = slugify(title)
    return "uploads/%s-%s" % (slug, filename)


class Images(models.Model):
    personal = models.ForeignKey(Personal, default=None, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to=get_image_filename,
                              verbose_name="Image")