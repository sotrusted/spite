"""
Celery tasks for content analysis
"""

import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

from .analysis import ContentAnalysisManager
from .models import AnalysisSettings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, priority=1)  # Low priority
def analyze_content_sentiment(self, max_items=None):
    """
    Celery task to analyze sentiment of posts and comments
    """
    try:
        manager = ContentAnalysisManager()
        processed_count = manager.analyze_sentiment_batch(max_items)
        
        logger.info(f"Sentiment analysis task completed: {processed_count} items processed")
        return {
            'status': 'success',
            'processed_count': processed_count,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Sentiment analysis task failed: {exc}")
        if self.request.retries < self.max_retries:
            # Retry with exponential backoff
            countdown = 2 ** self.request.retries * 60  # 1, 2, 4 minutes
            raise self.retry(exc=exc, countdown=countdown)
        else:
            return {
                'status': 'error',
                'error': str(exc),
                'timestamp': timezone.now().isoformat()
            }


@shared_task(bind=True, max_retries=3, priority=1)  # Low priority
def generate_semantic_analysis(self, period_type='hour'):
    """
    Celery task to generate semantic analysis for time periods
    """
    try:
        manager = ContentAnalysisManager()
        success = manager.generate_semantic_analysis(period_type)
        
        if success:
            logger.info(f"Semantic analysis task completed for period: {period_type}")
            return {
                'status': 'success',
                'period_type': period_type,
                'timestamp': timezone.now().isoformat()
            }
        else:
            return {
                'status': 'skipped',
                'reason': 'No new content or analysis disabled',
                'period_type': period_type,
                'timestamp': timezone.now().isoformat()
            }
        
    except Exception as exc:
        logger.error(f"Semantic analysis task failed for {period_type}: {exc}")
        if self.request.retries < self.max_retries:
            countdown = 2 ** self.request.retries * 60
            raise self.retry(exc=exc, countdown=countdown)
        else:
            return {
                'status': 'error',
                'error': str(exc),
                'period_type': period_type,
                'timestamp': timezone.now().isoformat()
            }


@shared_task(bind=True, priority=1)  # Low priority
def run_full_content_analysis(self):
    """
    Comprehensive analysis task that runs both sentiment and semantic analysis
    """
    try:
        settings = AnalysisSettings.get_settings()
        
        if not settings.sentiment_analysis_enabled and not settings.semantic_analysis_enabled:
            return {
                'status': 'skipped',
                'reason': 'All analysis disabled in settings',
                'timestamp': timezone.now().isoformat()
            }
        
        manager = ContentAnalysisManager()
        results = manager.run_full_analysis()
        
        logger.info(f"Full analysis completed: {results}")
        return {
            'status': 'success',
            'results': results,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Full analysis task failed: {exc}")
        return {
            'status': 'error',
            'error': str(exc),
            'timestamp': timezone.now().isoformat()
        }


@shared_task(priority=1)  # Low priority
def cleanup_old_analysis_data():
    """
    Cleanup old analysis data to prevent database bloat
    """
    try:
        from .models import SentimentAnalysis, SemanticAnalysis
        
        # Remove sentiment analysis older than 30 days
        cutoff_date = timezone.now() - timedelta(days=30)
        
        deleted_sentiment = SentimentAnalysis.objects.filter(
            analyzed_at__lt=cutoff_date
        ).delete()
        
        # Remove semantic analysis older than 90 days
        semantic_cutoff = timezone.now() - timedelta(days=90)
        deleted_semantic = SemanticAnalysis.objects.filter(
            created_at__lt=semantic_cutoff
        ).delete()
        
        logger.info(f"Cleanup completed: {deleted_sentiment[0]} sentiment records, {deleted_semantic[0]} semantic records deleted")
        
        return {
            'status': 'success',
            'deleted_sentiment': deleted_sentiment[0],
            'deleted_semantic': deleted_semantic[0],
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Cleanup task failed: {exc}")
        return {
            'status': 'error',
            'error': str(exc),
            'timestamp': timezone.now().isoformat()
        }
