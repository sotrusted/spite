import uuid
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.urls import reverse
from django.template.defaultfilters import slugify
from django.db import models
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify
import mimetypes
from django.core.exceptions import ValidationError

def validate_media_file(value):
    """Validate that the file is either an image or a video."""
    mime_type, _ = mimetypes.guess_type(value.name)
    if not mime_type or not mime_type.startswith(('image/', 'video/')):
        raise ValidationError("File must be an image or a video.")

def validate_video_file_size(file):
    max_size_mb = 50
    if file.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"File size exceeds {max_size_mb} MB.")


class Post(models.Model):
    #not implemented
    author = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True) 
    anon_uuid = models.UUIDField(default=uuid.uuid4, editable=False)

    #text fields
    title = models.CharField(max_length=100, verbose_name='What\'s your problem?')
    content = models.TextField(verbose_name='content', default='', null=True, blank=True)
    display_name = models.CharField(max_length=100, verbose_name='Display Name', null=True, blank=True, default='')

    #media fields
    image = models.ImageField(blank=True, null=True, verbose_name=f'image', upload_to='images/')
    media_file = models.FileField(upload_to='media/', blank=True, null=True, \
                                max_length=255, verbose_name = 'Image or video (<50 MB)', \
                                validators=[validate_media_file, validate_video_file_size])  # New field

    #meta
    date_posted = models.DateTimeField(auto_now_add=True)
    is_pinned = models.BooleanField(default=False)
    #meta/not implemented
    like_count = models.PositiveIntegerField(default=0)
    parent_post = models.ForeignKey('self',null=True,blank=True,related_name='replies',on_delete=models.CASCADE)
    


    # deprecated
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name='city or neighborhood')
    contact = models.TextField(blank=True, null=True, verbose_name='contact info')
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('post-detail', kwargs={'pk' : self.pk})

    def save(self, *args, **kwargs):
        super(Post, self).save(*args, **kwargs)
    
    def is_image(self):
        """Check if the media_file is an image."""
        mime_type, _ = mimetypes.guess_type(self.media_file.name if self.media_file else self.image.name)
        return mime_type and mime_type.startswith('image/')

    def is_video(self):
        """Check if the media_file is a video."""
        if not self.media_file: 
            return False
        mime_type, _ = mimetypes.guess_type(self.media_file.name if self.media_file else None)
        return mime_type and mime_type.startswith('video/')
    
    def get_recent_comments(self):
        return Comment.objects.filter(post=self).order_by('-created_on')


def get_image_filename(instance, filename):
    title = instance.personal.title
    slug = slugify(title)
    return "uploads/%s-%s" % (slug, filename)


class Comment(models.Model):
    post = models.ForeignKey(Post, related_name='comments', on_delete=models.CASCADE)
    name = models.CharField(max_length=100, blank=True)  # Optional name field
    content = models.TextField()
    created_on = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f'Comment by {self.name or "Anonymous"} on {self.post}'