import uuid
import logging
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.timezone import now
from django.template.defaultfilters import slugify
from django.db import models
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify
import mimetypes
from django.core.exceptions import ValidationError

logger = logging.getLogger('spite')

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
        return f'{self.id} - {self.title}'

    def print_long(self):
        # Build the main post string
        posts_string = f'{self.title}-{self.content}-by {self.display_name or "anon"}'
        logger.info(f"Post String: {posts_string}")

        # Fetch recent comments
        comments = self.get_recent_comments()
        logger.info(f"Comments QuerySet for post {self.id}: {comments}")

        try:
            if comments.exists():  # Check if comments exist
                # Build a string of all comments
                comments_string = 'Comments:' 
                for comment in comments:
                    comments_string += '\n' + str(comment)
                logger.info(f"Comments String for post {self.id}: {comments_string}")
                return posts_string + '\n' + comments_string
            else:
                logger.info(f"No comments found for post {self.id}.")
                return posts_string
        except Exception as e:
            logger.error(f"Error in print_long for post {self.id}: {e}")
            return posts_string

    def get_item_type(self):
        return "Post"
        
    
    def get_absolute_url(self):
        return reverse('post-detail', kwargs={'pk' : self.pk})

    def save(self, *args, **kwargs):
        super(Post, self).save(*args, **kwargs)
    
    def is_image(self):
        """Check if the media_file is an image."""
        if self.image: 
            return True
        if not self.media_file: 
            return False
        mime_type, _ = mimetypes.guess_type(self.media_file.name if self.media_file else self.image.name)
        return mime_type and mime_type.startswith('image/')

    def is_video(self):
        """Check if the media_file is a video."""
        if self.image:
            return False
        if not self.media_file: 
            return False
        mime_type, _ = mimetypes.guess_type(self.media_file.name if self.media_file else None)
        return mime_type and mime_type.startswith('video/')
    
    def get_recent_comments(self):
        comments = Comment.objects.filter(post=self).order_by('-created_on')
        return comments


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
        return f'{self.name or "anon"}: \"{self.content}\" on {self.post.title}'

    def get_item_type(self):
        return "Comment"

class SearchQueryLog(models.Model):
    query = models.CharField(max_length=255)
    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.query} - {self.timestamp}"


class Summary(models.Model):
    start_index = models.IntegerField(blank=True,null=True)  # The first post in the range
    end_index = models.IntegerField(blank=True,null=True)    # The last post in the range
    title = models.CharField(max_length=100)
    summary = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

class PageView(models.Model):
    count = models.PositiveBigIntegerField(default=0)
