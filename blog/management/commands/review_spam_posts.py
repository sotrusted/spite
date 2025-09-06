from blog.models import Post, Comment
from django.core.management.base import BaseCommand
from django.utils import timezone

class Command(BaseCommand):
    help = 'Check spam posts'

    def handle(self, *args, **options):
        posts = Post.objects.filter(spam_score__gt=40, reviewed=False)
        for post in posts:
            print(post.title)
            print(post.content[:100])
            print(post.display_name)
            print(post.media_file)
            print(post.date_posted)
            print(post.spam_score)
            print(post.spam_reasons)
            print('--------------------------------')
            restore = input('Restore? (y/n)')
            if restore == 'y':
                post.spam_score = 0
                post.spam_reasons = None
                post.date_posted = timezone.now()
                post.restored = True
            post.reviewed = True
            post.save()
            

        comments = Comment.objects.filter(spam_score__gt=40, reviewed=False)
        for comment in comments:
            print(comment.content[:100])
            print(comment.name)
            print(comment.media_file)
            print(comment.created_on)
            print(comment.spam_score)
            print(comment.spam_reasons)
            print('--------------------------------')
            restore = input('Restore? (y/n)')
            if restore == 'y':
                comment.spam_score = 0
                comment.spam_reasons = None
                comment.created_on = timezone.now()
                comment.restored = True
            comment.reviewed = True
            comment.save()