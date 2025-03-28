from django.core.management.base import BaseCommand
from blog.models import Post, Comment, List, SearchQueryLog
from datetime import datetime

class Command(BaseCommand):
    help = 'Collate all posts into a text file'

    def handle(self, *args, **kwargs):
        # Retrieve all posts
        posts = Post.objects.all()
        comments = Comment.objects.all()
        list = List.objects.all()
        searches = SearchQueryLog.objects.all()

        # Generate a filename with the current date
        current_date = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = f'all_text_{current_date}.txt'

        # Open a text file for writing
        with open(filename, 'w+') as file:
            self.write_posts(file, posts)
            self.write_comments(file, comments)
            self.write_list(file, list)
            self.write_searchquery(file, searches)

        self.stdout.write(self.style.SUCCESS(f'Successfully collated all text into {filename}'))
    
    def write_posts(self, file, posts):
        self.stdout.write(self.style.HTTP_INFO(f'Writing {posts.count()} posts'))
        file.write('//Post//')
        for post in posts:
            file.write(f'{post.title}\n')
            file.write(f'{post.content}\n')
            if post.image:
                file.write(f'{post.image.url}\n')
            elif post.media_file:
                file.write(f'{post.media_file.url}\n')
            if post.display_name:
                file.write(f'by {post.display_name}\n')

    def write_comments(self, file, comments):
        self.stdout.write(self.style.HTTP_INFO(f'Writing {comments.count()} comments'))

        file.write('//Comment//')
        for comment in comments:
            if comment.name:
                file.write(f'{comment.name}')
            file.write(f'{comment.content}')

    def write_list(self,file, list):
        self.stdout.write(self.style.HTTP_INFO(f'Writing {list.count()} list entries'))

        file.write('//List//')
        for input in list:
            if input.input:
                file.write(f'{input.input}')

    def write_searchquery(self, file, searches):
        self.stdout.write(self.style.HTTP_INFO(f'Writing {searches.count()} search queries'))

        file.write('//SearchQueryLog//')
        for search in searches:
            if search.query:
                file.write(f'{search.query}')
