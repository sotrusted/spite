import pandas as pd
from blog.models import Post, Comment
from itertools import chain
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Export posts to a CSV file'

    def handle(self, *args, **kwargs):
        posts = Post.objects.all()
        posts_values = posts.values('id', 'title', 'content', 'date_posted', 'display_name', 'ip_address')
        comments = Comment.objects.all()
        comments_values = comments.values('id', 'post', 'parent_comment', 'content', 'created_on',  'ip_address')

        posts_df = pd.DataFrame(posts_values)
        comments_df = pd.DataFrame(comments_values)

        posts_df.to_csv('posts.csv', index=False)
        comments_df.to_csv('comments.csv', index=False)
