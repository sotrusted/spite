import logging
from django.core.management.base import BaseCommand
from django.core.cache import cache

logger = logging.getLogger('spite')
class Command(BaseCommand):
    help = 'Clears the entire cache'

    def handle(self, *args, **kwargs):
        self.stdout.write('Clearing cache...')
        logger.info('Cache clearing process started.')
        cache.clear()
        self.stdout.write(self.style.SUCCESS('Cache cleared successfully.'))
        logger.info('Cache cleared successfully.')
