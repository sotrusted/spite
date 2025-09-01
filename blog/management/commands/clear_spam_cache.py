from django.core.management.base import BaseCommand
from django.core.cache import cache
from blog.views import PostCreateView
import logging

logger = logging.getLogger('spite')

class Command(BaseCommand):
    help = 'Clear spam detection caches'

    def add_arguments(self, parser):
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Show spam detection statistics before clearing',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleared without actually clearing',
        )

    def handle(self, *args, **options):
        if options['stats']:
            self.show_stats()
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING('DRY RUN - No caches will be cleared')
            )
            return
        
        # Create a temporary instance to access the method
        temp_view = PostCreateView()
        
        try:
            temp_view.clear_spam_caches()
            self.stdout.write(
                self.style.SUCCESS('Successfully cleared spam caches')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error clearing spam caches: {e}')
            )
    
    def show_stats(self):
        """Display current spam detection statistics"""
        try:
            global_posts = cache.get('global_recent_posts_fast', [])
            global_images = cache.get('global_recent_images', [])
            
            self.stdout.write('Spam Detection Statistics:')
            self.stdout.write(f'  Global posts in cache: {len(global_posts)}')
            self.stdout.write(f'  Global images in cache: {len(global_images)}')
            
            if global_posts:
                self.stdout.write('\nRecent global posts:')
                for i, post in enumerate(global_posts[-5:], 1):
                    preview = post[:100] + '...' if len(post) > 100 else post
                    self.stdout.write(f'  {i}. {preview}')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error getting stats: {e}')
            ) 