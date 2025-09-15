"""
Management command to run content analysis
"""

from django.core.management.base import BaseCommand
from blog.analysis import ContentAnalysisManager
from blog.tasks import run_full_content_analysis
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run content analysis (sentiment and semantic)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--async',
            action='store_true',
            help='Run analysis as Celery task (requires Celery worker)',
        )
        parser.add_argument(
            '--max-items',
            type=int,
            default=None,
            help='Maximum number of items to process',
        )
        parser.add_argument(
            '--sentiment-only',
            action='store_true',
            help='Run only sentiment analysis',
        )
        parser.add_argument(
            '--semantic-only',
            action='store_true',
            help='Run only semantic analysis',
        )

    def handle(self, *args, **options):
        if options['async']:
            self.stdout.write('Queuing analysis task...')
            task = run_full_content_analysis.delay()
            self.stdout.write(
                self.style.SUCCESS(f'Analysis task queued with ID: {task.id}')
            )
            return

        # Run synchronously
        manager = ContentAnalysisManager()
        
        if options['sentiment_only']:
            self.stdout.write('Running sentiment analysis...')
            count = manager.analyze_sentiment_batch(options['max_items'])
            self.stdout.write(
                self.style.SUCCESS(f'Analyzed sentiment for {count} items')
            )
            
        elif options['semantic_only']:
            self.stdout.write('Running semantic analysis...')
            results = {}
            for period in ['hour', 'day', 'week']:
                if manager.generate_semantic_analysis(period):
                    results[period] = True
                    
            completed = len([p for p, success in results.items() if success])
            self.stdout.write(
                self.style.SUCCESS(f'Generated semantic analysis for {completed} periods')
            )
            
        else:
            self.stdout.write('Running full content analysis...')
            results = manager.run_full_analysis()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Analysis complete:\n'
                    f'  - Sentiment analyzed: {results["sentiment_analyzed"]} items\n'
                    f'  - Semantic periods: {results["semantic_periods_generated"]}'
                )
            )
