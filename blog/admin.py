from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import path
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count
from .models import \
    Post, Comment, SearchQueryLog, ChatMessage, List, BlockedIP, SentimentAnalysis, \
         SemanticAnalysis, AnalysisSettings, AIChatSession, SiteNotification
from axes.models import AccessFailureLog, AccessAttempt, AccessLog
import logging

logger = logging.getLogger('spite')

class CustomAdminSite(admin.AdminSite):
    site_header = "SPITE Magazine Admin"
    site_title = "SPITE Admin"
    index_title = "Welcome to SPITE Magazine Administration"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_view(self.dashboard_view), name='admin_dashboard'),
            path('dashboard/api/', self.admin_view(self.dashboard_api), name='admin_dashboard_api'),
        ]
        return custom_urls + urls
    
    def dashboard_view(self, request):
        """Admin dashboard with posts and comments metrics"""
        try:
            now = timezone.now()
            
            # Time ranges
            one_hour_ago = now - timedelta(hours=1)
            twelve_hours_ago = now - timedelta(hours=12)
            one_day_ago = now - timedelta(days=1)
            one_week_ago = now - timedelta(weeks=1)
            one_month_ago = now - timedelta(days=30)
            
            # Posts metrics
            posts_last_hour = Post.objects.filter(date_posted__gte=one_hour_ago).count()
            posts_last_12h = Post.objects.filter(date_posted__gte=twelve_hours_ago).count()
            posts_last_day = Post.objects.filter(date_posted__gte=one_day_ago).count()
            posts_last_week = Post.objects.filter(date_posted__gte=one_week_ago).count()
            posts_last_month = Post.objects.filter(date_posted__gte=one_month_ago).count()
            
            # Comments metrics
            comments_last_hour = Comment.objects.filter(created_on__gte=one_hour_ago).count()
            comments_last_12h = Comment.objects.filter(created_on__gte=twelve_hours_ago).count()
            comments_last_day = Comment.objects.filter(created_on__gte=one_day_ago).count()
            comments_last_week = Comment.objects.filter(created_on__gte=one_week_ago).count()
            comments_last_month = Comment.objects.filter(created_on__gte=one_month_ago).count()
            
            # Hourly data for charts (last 24 hours)
            posts_hourly_raw = Post.objects.filter(
                date_posted__gte=now - timedelta(days=1)
            ).extra(
                select={'hour': 'EXTRACT(hour FROM date_posted)'}
            ).values('hour').annotate(count=Count('id')).order_by('hour')
            
            comments_hourly_raw = Comment.objects.filter(
                created_on__gte=now - timedelta(days=1)
            ).extra(
                select={'hour': 'EXTRACT(hour FROM created_on)'}
            ).values('hour').annotate(count=Count('id')).order_by('hour')
            
            # Convert Decimal hour values to integers
            posts_hourly = [{'hour': int(item['hour']), 'count': item['count']} for item in posts_hourly_raw]
            comments_hourly = [{'hour': int(item['hour']), 'count': item['count']} for item in comments_hourly_raw]
            
            # Daily data for charts (last 30 days)
            posts_daily_raw = Post.objects.filter(
                date_posted__gte=now - timedelta(days=30)
            ).extra(
                select={'day': 'DATE(date_posted)'}
            ).values('day').annotate(count=Count('id')).order_by('day')
            
            comments_daily_raw = Comment.objects.filter(
                created_on__gte=now - timedelta(days=30)
            ).extra(
                select={'day': 'DATE(created_on)'}
            ).values('day').annotate(count=Count('id')).order_by('day')
            
            # Convert dates to strings for Chart.js
            posts_daily = [{'day': item['day'].isoformat(), 'count': item['count']} for item in posts_daily_raw]
            comments_daily = [{'day': item['day'].isoformat(), 'count': item['count']} for item in comments_daily_raw]
            
            # Recent posts and comments
            recent_posts = Post.objects.select_related().order_by('-date_posted')[:10]
            recent_comments = Comment.objects.select_related('post').order_by('-created_on')[:10]
            
            # Analysis data
            try:
                # Quick visibility into what exists
                total_sentiment = SentimentAnalysis.objects.count()
                total_semantic = SemanticAnalysis.objects.count()
                logger.info(f"[Dashboard] SentimentAnalysis count: {total_sentiment}")
                logger.info(f"[Dashboard] SemanticAnalysis count: {total_semantic}")

                # Sentiment analysis stats
                sentiment_stats = {
                    'total_analyzed': SentimentAnalysis.objects.count(),
                    'avg_sentiment_7d': 0.0,
                    'sentiment_trend': [],
                }
                
                # Get recent sentiment data for trend (last 30 days for better time series)
                recent_sentiment = SentimentAnalysis.objects.filter(
                    analyzed_at__gte=now - timedelta(days=30)
                ).values_list('sentiment_score', 'analyzed_at').order_by('analyzed_at')
                logger.info(f"[Dashboard] Recent sentiment queryset len: {recent_sentiment.count()}")

                
                if recent_sentiment:
                    # Calculate 7-day average
                    recent_7d = [score for score, date in recent_sentiment if date >= now - timedelta(days=7)]
                    sentiment_stats['avg_sentiment_7d'] = sum(recent_7d) / len(recent_7d) if recent_7d else 0.0
                    logger.info(f"[Dashboard] Computed avg_sentiment_7d over {len(recent_7d)} records: {sentiment_stats['avg_sentiment_7d']}")

                        
                    # Group by day for trend (last 30 days)
                    from collections import defaultdict
                    daily_sentiment = defaultdict(list)
                    for score, analyzed_at in recent_sentiment:
                        day = analyzed_at.date().isoformat()
                        daily_sentiment[day].append(score)
                    
                    # Create time series data for last 30 days
                    sentiment_trend = []
                    for i in range(30):
                        date = (now - timedelta(days=29-i)).date()
                        day_key = date.isoformat()
                        if day_key in daily_sentiment:
                            avg_sentiment = sum(daily_sentiment[day_key]) / len(daily_sentiment[day_key])
                            sentiment_trend.append({
                                'day': day_key,
                                'date': date.strftime('%m-%d'),
                                'avg_sentiment': round(avg_sentiment, 3),
                                'count': len(daily_sentiment[day_key])
                            })
                        else:
                            sentiment_trend.append({
                                'day': day_key,
                                'date': date.strftime('%m-%d'),
                                'avg_sentiment': 0,
                                'count': 0
                            })
                    
                    sentiment_stats['sentiment_trend'] = sentiment_trend
                    logger.info(f"[Dashboard] Built sentiment_trend with {len(sentiment_trend)} days")
                    
                    # Add hourly sentiment for recent day (last 24 hours instead of just "today")
                    from django.db.models import Avg
                    last_24h_sentiment = SentimentAnalysis.objects.filter(
                        analyzed_at__gte=now - timedelta(hours=24)
                    ).extra(
                        select={'hour': 'EXTRACT(hour FROM analyzed_at)'}
                    ).values('hour').annotate(
                        avg_sentiment=Avg('sentiment_score'),
                        count=Count('id')
                    ).order_by('hour')
                    
                    sentiment_stats['hourly_sentiment'] = [
                        {'hour': int(item['hour']), 'avg_sentiment': float(item['avg_sentiment']), 'count': item['count']}
                        for item in last_24h_sentiment
                    ]
                    logger.info(f"[Dashboard] Hourly sentiment buckets (last 24h): {len(sentiment_stats['hourly_sentiment'])}")
                
                # Semantic analysis stats  
                semantic_stats = {
                    'total_periods': SemanticAnalysis.objects.count(),
                    'recent_topics': {},
                    'keyword_cloud': {},
                }
                
                # Get recent semantic data
                recent_semantic = SemanticAnalysis.objects.filter(
                    period_type='day',
                    period_start__gte=now - timedelta(days=7)
                ).order_by('-period_start')[:7]
                logger.info(f"[Dashboard] Recent semantic periods fetched: {recent_semantic.count() if hasattr(recent_semantic, 'count') else len(recent_semantic)}")
                
                if recent_semantic:
                    # Aggregate topics from recent periods
                    all_topics = {}
                    all_keywords = {}
                    
                    for analysis in recent_semantic:
                        for topic, score in analysis.topic_distribution.items():
                            all_topics[topic] = all_topics.get(topic, 0) + score
                        
                        for keyword, count in analysis.keyword_frequency.items():
                            all_keywords[keyword] = all_keywords.get(keyword, 0) + count
                    
                    # Normalize and get top items
                    total_topic_score = sum(all_topics.values())
                    if total_topic_score > 0:
                        semantic_stats['recent_topics'] = {
                            topic: score/total_topic_score 
                            for topic, score in sorted(all_topics.items(), key=lambda x: x[1], reverse=True)[:5]
                        }
                    
                    semantic_stats['keyword_cloud'] = dict(
                        sorted(all_keywords.items(), key=lambda x: x[1], reverse=True)[:20]
                    )
                    logger.info(f"[Dashboard] Built semantic recent_topics: {len(semantic_stats['recent_topics'])}, keyword_cloud: {len(semantic_stats['keyword_cloud'])}")
                
                # Analysis settings
                analysis_settings = AnalysisSettings.get_settings()
                
            except Exception as e:
                # Fallback if analysis models not ready
                logger.exception(f"[Dashboard] Error while building analysis data: {e}")
                sentiment_stats = {'total_analyzed': 0, 'avg_sentiment_7d': 0.0, 'sentiment_trend': []}
                semantic_stats = {'total_periods': 0, 'recent_topics': {}, 'keyword_cloud': {}}
                analysis_settings = None
            
            context = {
                **self.each_context(request),
                'title': 'Dashboard',
                'posts_metrics': {
                    'hour': posts_last_hour,
                    'twelve_hours': posts_last_12h,
                    'day': posts_last_day,
                    'week': posts_last_week,
                    'month': posts_last_month,
                },
                'comments_metrics': {
                    'hour': comments_last_hour,
                    'twelve_hours': comments_last_12h,
                    'day': comments_last_day,
                    'week': comments_last_week,
                    'month': comments_last_month,
                },
                'posts_hourly': posts_hourly,
                'comments_hourly': comments_hourly,
                'posts_daily': posts_daily,
                'comments_daily': comments_daily,
                'recent_posts': recent_posts,
                'recent_comments': recent_comments,
                'sentiment_stats': sentiment_stats,
                'semantic_stats': semantic_stats,
                'analysis_settings': analysis_settings,
            }
            
            return TemplateResponse(request, 'admin/dashboard.html', context)
            
        except Exception as e:
            context = {
                **self.each_context(request),
                'title': 'Dashboard Error',
                'error': str(e),
            }
            return TemplateResponse(request, 'admin/dashboard_error.html', context)
    
    def dashboard_api(self, request):
        """API endpoint for dashboard data updates"""
        try:
            now = timezone.now()
            
            # Time ranges
            one_hour_ago = now - timedelta(hours=1)
            twelve_hours_ago = now - timedelta(hours=12)
            one_day_ago = now - timedelta(days=1)
            one_week_ago = now - timedelta(weeks=1)
            one_month_ago = now - timedelta(days=30)
            
            # Posts metrics
            posts_metrics = {
                'hour': Post.objects.filter(date_posted__gte=one_hour_ago).count(),
                'twelve_hours': Post.objects.filter(date_posted__gte=twelve_hours_ago).count(),
                'day': Post.objects.filter(date_posted__gte=one_day_ago).count(),
                'week': Post.objects.filter(date_posted__gte=one_week_ago).count(),
                'month': Post.objects.filter(date_posted__gte=one_month_ago).count(),
            }
            
            # Comments metrics
            comments_metrics = {
                'hour': Comment.objects.filter(created_on__gte=one_hour_ago).count(),
                'twelve_hours': Comment.objects.filter(created_on__gte=twelve_hours_ago).count(),
                'day': Comment.objects.filter(created_on__gte=one_day_ago).count(),
                'week': Comment.objects.filter(created_on__gte=one_week_ago).count(),
                'month': Comment.objects.filter(created_on__gte=one_month_ago).count(),
            }
            
            data = {
                'posts_metrics': posts_metrics,
                'comments_metrics': comments_metrics,
                'timestamp': now.isoformat(),
            }
            
            return JsonResponse(data)
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

# Create custom admin site instance
admin_site = CustomAdminSite(name='admin')

# Register models with custom admin site
admin_site.register(Post)
admin_site.register(Comment)
admin_site.register(SearchQueryLog)
admin_site.register(ChatMessage)
admin_site.register(List)
admin_site.register(SentimentAnalysis)
admin_site.register(SemanticAnalysis)
admin_site.register(AnalysisSettings)
admin_site.register(AIChatSession)
admin_site.register(SiteNotification)

class BlockedIPAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'ip_range', 'reason', 'date_blocked', 'is_permanent', 'expires', 'is_active')
    list_filter = ('is_permanent', 'date_blocked')
    search_fields = ('ip_address', 'ip_range', 'reason')

admin_site.register(BlockedIP, BlockedIPAdmin)

# Register axes models with custom admin site
admin_site.register(AccessFailureLog)
admin_site.register(AccessAttempt)
admin_site.register(AccessLog)

# Also register with default admin for compatibility
admin.site.register(Post)   
admin.site.register(Comment)
admin.site.register(SearchQueryLog)
admin.site.register(ChatMessage)
admin.site.register(List)
admin.site.register(BlockedIP, BlockedIPAdmin)

admin.site.register(AIChatSession)
admin.site.register(SiteNotification)   