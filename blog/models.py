import uuid
from cryptography.fernet import Fernet, InvalidToken
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
from django.utils.functional import cached_property
from django.conf import settings
from django.core.cache import cache
class SecureIPStorage:
    def __init__(self):
        self.fernet = Fernet(settings.IP_ENCRYPTION_KEY)
    
    def encrypt_ip(self, ip):
        return self.fernet.encrypt(ip.encode()).decode()
    
    def decrypt_ip(self, encrypted_ip):
        try:
            # Try to decrypt if it's encrypted
            return self.fernet.decrypt(encrypted_ip.encode()).decode()
        except (InvalidToken, AttributeError):
            # If decryption fails or IP isn't encrypted yet, return as-is
            return encrypted_ip

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


def get_image_filename(instance, filename):
    title = instance.personal.title
    slug = slugify(title)
    return "uploads/%s-%s" % (slug, filename)



class Post(models.Model):
    #not implemented
    author = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True) 
    anon_uuid = models.UUIDField(default=uuid.uuid4, editable=False)

    #text fields
    title = models.CharField(max_length=100, verbose_name='What\'s your problem?', db_index=True)
    content = models.TextField(verbose_name='content', default='', null=True, blank=True)
    display_name = models.CharField(max_length=100, verbose_name='Display Name', null=True, blank=True, default='')

    #media fields
    image = models.ImageField(blank=True, null=True, verbose_name=f'image', upload_to='images/')
    media_file = models.FileField(upload_to='media/', blank=True, null=True, \
                                max_length=255, verbose_name = 'Image or video (<50 MB)', \
                                validators=[validate_media_file, validate_video_file_size])  # New field

    #meta
    date_posted = models.DateTimeField(auto_now_add=True, db_index=True)
    is_pinned = models.BooleanField(default=False, db_index=True)
    #meta/not implemented
    like_count = models.PositiveIntegerField(default=0)
    parent_post = models.ForeignKey('self',null=True,blank=True,related_name='replies',on_delete=models.CASCADE)

    # deprecated
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name='city or neighborhood')
    contact = models.TextField(blank=True, null=True, verbose_name='contact info')
    description = models.TextField(blank=True, null=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)

        # Encrypted IP storage
    encrypted_ip = models.CharField(max_length=255, null=True, blank=True)

    is_image = models.BooleanField(default=False)
    is_video = models.BooleanField(default=False)


    def __str__(self):
        return f'{self.id} - {self.title}'

    def print_long(self):
        # Build the main post string
        posts_string = f'{self.title}-{self.content}-by {self.display_name or "anon"}'
        # logger.info(f"Post String: {posts_string}")

        # Fetch recent comments
        comments = self.get_recent_comments()
        # logger.info(f"Comments QuerySet for post {self.id}: {comments}")

        try:
            if comments.exists():  # Check if comments exist
                # Build a string of all comments
                comments_string = 'Comments:' 
                for comment in comments:
                    comments_string += '\n' + str(comment)
                # logger.info(f"Comments String for post {self.id}: {comments_string}")
                return posts_string + '\n' + comments_string
            else:
                # logger.info(f"No comments found for post {self.id}.")
                return posts_string
        except Exception as e:
            # logger.error(f"Error in print_long for post {self.id}: {e}")
            return posts_string
    

    def get_item_type(self):
        return "Post"
        
    
    def get_absolute_url(self):
        return reverse('post-detail', kwargs={'pk' : self.pk})

    def save(self, *args, **kwargs):
        self.is_image = self.check_is_image()
        self.is_video = self.check_is_video()
        super(Post, self).save(*args, **kwargs)
    
    def check_is_image(self):
        """Check if the media_file is an image."""
        if self.image: 
            return True
        if not self.media_file: 
            return False
        mime_type, _ = mimetypes.guess_type(self.media_file.name if self.media_file else self.image.name)

        # Fallback for .png
        if not mime_type and (self.image.name.endswith('.png') or self.media_file.name.endswith('.png')):
            mime_type = 'image/png'

        return mime_type and mime_type.startswith('image/')

    def check_is_video(self):
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

    @property
    def comment_count(self):
        return self.comments.count()

    @cached_property
    def has_media(self):
        return bool(self.media_file or self.image)

    @cached_property
    def get_ip_address(self):
        storage = SecureIPStorage()
        return storage.decrypt_ip(self.encrypted_ip)
    
    def set_ip_address(self, value):
        storage = SecureIPStorage()
        self.encrypted_ip = storage.encrypt_ip(value)

    class Meta:
        indexes = [
            models.Index(fields=['-date_posted']),
            models.Index(fields=['is_pinned', '-date_posted']),
            # Add index for media fields if you query by them often
            models.Index(fields=['media_file', 'image']),
        ]


class Comment(models.Model):
    post = models.ForeignKey(Post, related_name='comments', on_delete=models.CASCADE)

    parent_comment = models.ForeignKey(
        'self',  # Self-referential foreign key for replies
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='replies'
    )
    name = models.CharField(max_length=100, blank=True)  # Optional name field
    content = models.TextField()
    created_on = models.DateTimeField(default=timezone.now)
    media_file = models.FileField(upload_to='media/', blank=True, null=True, \
                            max_length=255, verbose_name = 'Image or video (<50 MB)', \
                            validators=[validate_media_file, validate_video_file_size])  # New field

    ip_address = models.GenericIPAddressField(null=True, blank=True)

    @property
    def post_id(self):
        return self.post.id if self.post else None
    
    @property
    def post_display_name(self):
        return self.post.display_name if self.post and self.post.display_name else None
    
    @property
    def post_date_posted(self):
        return self.post.date_posted if self.post and self.post.date_posted else ''
    
    @property
    def post_media_file(self):
        return self.post.media_file if self.post and self.post.media_file else None

    @property
    def post_title(self):
        return self.post.title if self.post else ''

    @property
    def post_content(self):
        return self.post.content if self.post and self.post.content else ''

    @property
    def parent_comment_id(self):
        return self.parent_comment.id if self.parent_comment else None

    @property
    def parent_comment_content(self):
        return self.parent_comment.content if self.parent_comment and self.parent_comment.content else ''

    @property
    def parent_comment_name(self):
        return self.parent_comment.name if self.parent_comment and self.parent_comment.name else ''

    @property
    def parent_comment_media_file(self):
        return self.parent_comment.media_file if self.parent_comment and self.parent_comment.media_file else None   

    @property
    def parent_comment_is_image(self):
        return self.parent_comment.is_image if self.parent_comment and self.parent_comment.media_file else None

    @property
    def parent_comment_is_video(self):
        return self.parent_comment.is_video if self.parent_comment and self.parent_comment.media_file else None
    
    @property
    def parent_comment_media_file(self):
        return self.parent_comment.media_file if self.parent_comment and self.parent_comment.media_file else None

    @property
    def parent_comment_media_file_url(self):
        return self.parent_comment.media_file.url if self.parent_comment and self.parent_comment.media_file else ''

    @property
    def parent_comment_created_on(self):
        return self.parent_comment.created_on if self.parent_comment and self.parent_comment.created_on else ''

    @property 
    def post_image(self):
        return self.post.image if self.post and self.post.image else None
    
    @property
    def post_image_url(self):
        return self.post.image.url if self.post and self.post.image else ''

    @property
    def post_is_image(self):
        return self.post.is_image if self.post and (self.post.media_file or self.post.image) else None

    @property
    def post_is_video(self):
        return self.post.is_video if self.post and self.post.media_file else None

    @property
    def post_media_file_url(self):
        return self.post.media_file.url if self.post and self.post.media_file else ''


    def __str__(self):
        return f'{self.name or "Anonymous"}: \"{self.content}\" on {self.post.title}'

    def get_item_type(self):
        return "Comment"
    
    @cached_property
    def get_ip_address(self):
        storage = SecureIPStorage()
        return storage.decrypt_ip(self.encrypted_ip)
    
    def set_ip_address(self, value):
        storage = SecureIPStorage()
        self.encrypted_ip = storage.encrypt_ip(value)
    
    @cached_property
    def is_image(self):
        """Check if the media_file is an image."""
        logger.info(f"Checking is_image for comment {self.id}")
        logger.info(f"media_file: {self.media_file}")
        
        if not self.media_file: 
            logger.info("No media file")
            return False
            
        mime_type, _ = mimetypes.guess_type(self.media_file.name)
        logger.info(f"Mime type: {mime_type}")

        # Fallback for .png
        if not mime_type and self.media_file.name.endswith('.png'):
            logger.info("PNG fallback")
            mime_type = 'image/png'

        is_image = mime_type and mime_type.startswith('image/')
        logger.info(f"Is image: {is_image}")
        return is_image

    @cached_property
    def is_video(self):
        """Check if the media_file is a video."""
        logger.info(f"Checking is_video for comment {self.id}")
        logger.info(f"media_file: {self.media_file}")

        if hasattr(self, 'media_file') and not self.media_file: 
            return False

        mime_type, _ = mimetypes.guess_type(self.media_file.name if self.media_file else None)
        return mime_type and mime_type.startswith('video/')

    @cached_property
    def has_parent_comment(self):
        return self.parent_comment is not None \
            and hasattr(self.parent_comment, 'id') \
                and Comment.objects.filter(id=self.parent_comment.id).exists()
    

class SearchQueryLog(models.Model):
    query = models.CharField(max_length=255)
    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    encrypted_ip = models.CharField(max_length=255, null=True, blank=True)
    timestamp = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.query} - {self.timestamp}"

    @cached_property
    def get_ip_address(self):
        storage = SecureIPStorage()
        return storage.decrypt_ip(self.encrypted_ip)
    
    def set_ip_address(self, value):
        storage = SecureIPStorage()
        self.encrypted_ip = storage.encrypt_ip(value)


class Summary(models.Model):
    start_index = models.IntegerField(blank=True,null=True)  # The first post in the range
    end_index = models.IntegerField(blank=True,null=True)    # The last post in the range
    title = models.CharField(max_length=100)
    summary = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

class PageView(models.Model):
    count = models.PositiveBigIntegerField(default=0)

class List(models.Model):
    input = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    encrypted_ip = models.CharField(max_length=255, null=True, blank=True)

    @cached_property
    def get_ip_address(self):
        storage = SecureIPStorage()
        return storage.decrypt_ip(self.encrypted_ip)
    
    def set_ip_address(self, value):
        storage = SecureIPStorage()
        self.encrypted_ip = storage.encrypt_ip(value)

    def __str__(self):
        return self.input[:50]  # Show first 50 characters

# Cache individual post data
def get_post_data(post_id):
    cache_key = f'post_data_{post_id}'
    data = cache.get(cache_key)
    if data is None:
        data = Post.objects.get(id=post_id)
        cache.set(cache_key, data, 60 * 15)  # 15 minutes
    return data


class ChatMessage(models.Model):
    # Message metadata
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    chat_session = models.CharField(max_length=255, editable=False)  # To group messages from same chat session
    sender_id = models.UUIDField(editable=False)   # Anonymous user identifier
    
    # Message content
    message = models.TextField()
    message_type = models.CharField(max_length=20, choices=[
        ('message', 'Message'),
        ('status', 'Status'),
        ('matched', 'Matched'),
        ('disconnected', 'Disconnected')
    ])

    # Encrypted IP storage
    encrypted_ip = models.CharField(max_length=255, null=True, blank=True)
    
    # System metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
   
    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['chat_session']),
            models.Index(fields=['sender_id']),
        ]

    def __str__(self):
        return (f'[Chat {self.chat_session}] User {self.sender_id}@{self.ip_address}: {self.message}')

class BlockedIP(models.Model):
    ip_address = models.GenericIPAddressField(unique=True)
    reason = models.TextField(blank=True)
    date_blocked = models.DateTimeField(default=timezone.now)
    is_permanent = models.BooleanField(default=False)
    expires = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.ip_address} ({self.reason})"
    
    @property
    def is_active(self):
        if self.is_permanent:
            return True
        if self.expires and timezone.now() > self.expires:
            return False
        return True

    class Meta:
        db_table = 'blocked_ips'
