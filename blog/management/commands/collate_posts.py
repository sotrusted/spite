from django.core.management.base import BaseCommand
from blog.models import Post  # Adjust the import based on your app and model names
from datetime import datetime

class Command(BaseCommand):
    help = 'Collate all posts into a text file'

    def handle(self, *args, **kwargs):
        # Retrieve all posts
        posts = Post.objects.all()

        # Generate a filename with the current date
        current_date = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = f'all_posts_{current_date}.txt'

        # Open a text file for writing
        with open(filename, 'w+') as file:
            for post in posts:
                file.write(f'Title: {post.title}\n')
                file.write(f'Content:\n{post.content}\n')
                if post.image:
                    file.write(f'Media: {post.image.url}\n')
                elif post.media_file:
                    file.write(f'Media: {post.media_file.url}\n')
                if post.display_name:
                    file.write(f'Display Name: {post.display_name}\n')
                file.write('-' * 40 + '\n')

        self.stdout.write(self.style.SUCCESS(f'Successfully collated all posts into {filename}'))