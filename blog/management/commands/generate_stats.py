from django.core.management.base import BaseCommand
from blog.stats.query_stats import StatsGenerator
from datetime import datetime

class Command(BaseCommand):
    help = 'Generate statistics for search queries and list entries'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            default=f'reports/stats_report_{datetime.now().strftime("%Y%m%d%H%M%S")}.txt',
            help='Output file path'
        )

    def handle(self, *args, **options):
        stats = StatsGenerator()
        stats.generate_report(options['output'])
        self.stdout.write(
            self.style.SUCCESS('Successfully generated statistics report')
        ) 