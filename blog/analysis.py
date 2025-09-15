"""
Content Analysis Module for SPITE Magazine
Uses established libraries for sentiment and semantic analysis
"""

import logging
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

from django.utils import timezone
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType

from .models import Post, Comment, SentimentAnalysis, SemanticAnalysis, AnalysisSettings

logger = logging.getLogger(__name__)

# Try to import analysis libraries with fallbacks
try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False
    logger.warning("TextBlob not available. Install with: pip install textblob")

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import LatentDirichletAllocation
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available. Install with: pip install scikit-learn")

try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize
    from nltk.stem import WordNetLemmatizer
    NLTK_AVAILABLE = True
    
    # Download required NLTK data (only once)
    try:
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('corpora/stopwords')
        nltk.data.find('corpora/wordnet')
    except LookupError:
        logger.info("Downloading required NLTK data...")
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)
        nltk.download('wordnet', quiet=True)
        
except ImportError:
    NLTK_AVAILABLE = False
    logger.warning("NLTK not available. Install with: pip install nltk")


# Removed PerformanceMonitor - using Celery task priorities instead


class SentimentAnalyzer:
    """Sentiment analysis using TextBlob with fallback to simple lexicon"""
    
    def __init__(self):
        self.use_textblob = TEXTBLOB_AVAILABLE
        if not self.use_textblob:
            logger.warning("Using fallback sentiment analysis")
    
    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """
        Analyze sentiment of text
        Returns dict with sentiment_score, confidence, and emotions
        """
        if not text or len(text.strip()) < 3:
            return {
                'sentiment_score': 0.0,
                'confidence': 0.0,
                'emotion_joy': 0.0,
                'emotion_anger': 0.0,
                'emotion_fear': 0.0,
                'emotion_sadness': 0.0
            }
        
        if self.use_textblob:
            return self._analyze_with_textblob(text)
        else:
            return self._analyze_with_fallback(text)
    
    def _analyze_with_textblob(self, text: str) -> Dict[str, float]:
        """Analyze sentiment using TextBlob"""
        try:
            blob = TextBlob(text)
            
            # TextBlob returns polarity (-1 to 1) and subjectivity (0 to 1)
            polarity = blob.sentiment.polarity
            subjectivity = blob.sentiment.subjectivity
            
            # Use subjectivity as confidence measure
            confidence = min(1.0, subjectivity * 1.5)  # Scale subjective text higher
            
            # Simple emotion mapping based on polarity and word content
            emotions = self._extract_emotions_simple(text, polarity)
            
            return {
                'sentiment_score': polarity,
                'confidence': confidence,
                'emotion_joy': emotions.get('joy', 0.0),
                'emotion_anger': emotions.get('anger', 0.0),
                'emotion_fear': emotions.get('fear', 0.0),
                'emotion_sadness': emotions.get('sadness', 0.0)
            }
            
        except Exception as e:
            logger.error(f"TextBlob analysis failed: {e}")
            return self._analyze_with_fallback(text)
    
    def _extract_emotions_simple(self, text: str, polarity: float) -> Dict[str, float]:
        """Simple emotion detection based on keywords"""
        text_lower = text.lower()
        emotions = {'joy': 0.0, 'anger': 0.0, 'fear': 0.0, 'sadness': 0.0}
        
        # Emotion keywords
        joy_words = ['happy', 'joy', 'great', 'awesome', 'love', 'amazing', 'wonderful', 'excited']
        anger_words = ['angry', 'mad', 'furious', 'hate', 'annoyed', 'frustrated', 'outraged']
        fear_words = ['scared', 'afraid', 'worried', 'anxious', 'nervous', 'terrified']
        sadness_words = ['sad', 'depressed', 'disappointed', 'upset', 'miserable', 'heartbroken']
        
        total_words = len(text.split())
        
        for word in joy_words:
            if word in text_lower:
                emotions['joy'] += 0.3
        
        for word in anger_words:
            if word in text_lower:
                emotions['anger'] += 0.3
        
        for word in fear_words:
            if word in text_lower:
                emotions['fear'] += 0.3
        
        for word in sadness_words:
            if word in text_lower:
                emotions['sadness'] += 0.3
        
        # Adjust based on overall polarity
        if polarity > 0.1:
            emotions['joy'] += polarity * 0.5
        elif polarity < -0.1:
            if any(word in text_lower for word in anger_words):
                emotions['anger'] += abs(polarity) * 0.5
            else:
                emotions['sadness'] += abs(polarity) * 0.5
        
        # Normalize
        for emotion in emotions:
            emotions[emotion] = min(1.0, emotions[emotion])
        
        return emotions
    
    def _analyze_with_fallback(self, text: str) -> Dict[str, float]:
        """Fallback sentiment analysis using simple word counting"""
        positive_words = {'good', 'great', 'awesome', 'love', 'amazing', 'wonderful', 'excellent', 'fantastic', 'perfect', 'beautiful'}
        negative_words = {'bad', 'terrible', 'awful', 'hate', 'horrible', 'disgusting', 'stupid', 'worst', 'pathetic'}
        
        words = text.lower().split()
        positive_count = sum(1 for word in words if word.strip('.,!?";:()[]{}') in positive_words)
        negative_count = sum(1 for word in words if word.strip('.,!?";:()[]{}') in negative_words)
        
        total_sentiment_words = positive_count + negative_count
        total_words = len(words)
        
        if total_words == 0:
            return {'sentiment_score': 0.0, 'confidence': 0.0, 'emotion_joy': 0.0, 'emotion_anger': 0.0, 'emotion_fear': 0.0, 'emotion_sadness': 0.0}
        
        sentiment_score = (positive_count - negative_count) / max(total_words, 1)
        sentiment_score = max(-1.0, min(1.0, sentiment_score * 10))  # Scale up and clamp
        
        confidence = min(1.0, total_sentiment_words / max(total_words * 0.1, 1))
        
        emotions = self._extract_emotions_simple(text, sentiment_score)
        
        return {
            'sentiment_score': sentiment_score,
            'confidence': confidence,
            'emotion_joy': emotions.get('joy', 0.0),
            'emotion_anger': emotions.get('anger', 0.0),
            'emotion_fear': emotions.get('fear', 0.0),
            'emotion_sadness': emotions.get('sadness', 0.0)
        }


class SemanticAnalyzer:
    """Semantic analysis using sklearn and NLTK with fallbacks"""
    
    def __init__(self):
        self.use_advanced = SKLEARN_AVAILABLE and NLTK_AVAILABLE
        self.use_nltk = NLTK_AVAILABLE
        
        if self.use_nltk:
            self.stop_words = set(stopwords.words('english'))
            self.lemmatizer = WordNetLemmatizer()
        else:
            self.stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
    
    def extract_keywords(self, text: str, max_keywords: int = 20) -> Dict[str, int]:
        """Extract meaningful keywords from text"""
        if not text:
            return {}
        
        if self.use_nltk:
            return self._extract_keywords_nltk(text, max_keywords)
        else:
            return self._extract_keywords_simple(text, max_keywords)
    
    def _extract_keywords_nltk(self, text: str, max_keywords: int) -> Dict[str, int]:
        """Extract keywords using NLTK"""
        try:
            # Tokenize and lemmatize
            tokens = word_tokenize(text.lower())
            lemmatized = [
                self.lemmatizer.lemmatize(token) 
                for token in tokens 
                if token.isalpha() and len(token) > 2 and token not in self.stop_words
            ]
            
            # Count frequency
            word_counts = Counter(lemmatized)
            return dict(word_counts.most_common(max_keywords))
            
        except Exception as e:
            logger.error(f"NLTK keyword extraction failed: {e}")
            return self._extract_keywords_simple(text, max_keywords)
    
    def _extract_keywords_simple(self, text: str, max_keywords: int) -> Dict[str, int]:
        """Simple keyword extraction with better filtering"""
        # Extended stop words for better filtering
        extended_stop_words = self.stop_words.union({
            'that', 'this', 'have', 'been', 'just', 'like', 'some', 'what', 
            'when', 'they', 'your', 'feel', 'because', 'body', 'brain',
            'system', 'studies', 'food', 'sugar', 'want', 'know', 'think',
            'really', 'still', 'also', 'even', 'more', 'most', 'much',
            'many', 'make', 'made', 'take', 'taken', 'give', 'given',
            'come', 'came', 'went', 'going', 'said', 'says', 'way',
            'ways', 'time', 'times', 'good', 'bad', 'big', 'small',
            'new', 'old', 'first', 'last', 'long', 'short', 'high', 'low'
        })
        
        words = text.lower().split()
        meaningful_words = []
        
        for word in words:
            cleaned_word = word.strip('.,!?";:()[]{}')
            # Filter by length, stop words, and exclude pure numbers
            if (len(cleaned_word) > 4 and 
                cleaned_word not in extended_stop_words and
                not cleaned_word.isdigit() and
                cleaned_word.isalpha()):  # Only alphabetic words
                meaningful_words.append(cleaned_word)
        
        word_counts = Counter(meaningful_words)
        return dict(word_counts.most_common(max_keywords))
    
    def detect_topics(self, texts: List[str], n_topics: int = 5) -> Dict[str, float]:
        """Detect topics using LDA or fallback to keyword matching"""
        if not texts:
            return {}
        
        if self.use_advanced and len(texts) > 5:  # Need multiple docs for LDA
            return self._detect_topics_lda(texts, n_topics)
        else:
            return self._detect_topics_simple(" ".join(texts))
    
    def _detect_topics_lda(self, texts: List[str], n_topics: int) -> Dict[str, float]:
        """Topic detection using Latent Dirichlet Allocation"""
        try:
            # Vectorize text
            vectorizer = TfidfVectorizer(
                max_features=100,
                stop_words='english',
                ngram_range=(1, 2),
                min_df=2,
                max_df=0.8
            )
            
            doc_term_matrix = vectorizer.fit_transform(texts)
            
            if doc_term_matrix.shape[0] < n_topics:
                n_topics = max(1, doc_term_matrix.shape[0] - 1)
            
            # Fit LDA model
            lda = LatentDirichletAllocation(
                n_components=n_topics,
                random_state=42,
                max_iter=10,  # Limit iterations for performance
                learning_method='online'
            )
            
            lda.fit(doc_term_matrix)
            
            # Get feature names
            feature_names = vectorizer.get_feature_names_out()
            
            # Extract topics
            topics = {}
            for topic_idx, topic in enumerate(lda.components_):
                top_words = [feature_names[i] for i in topic.argsort()[-10:][::-1]]
                topic_name = f"topic_{topic_idx + 1}"
                
                # Simple topic labeling based on top words
                if any(word in top_words for word in ['tech', 'computer', 'software', 'internet']):
                    topic_name = 'technology'
                elif any(word in top_words for word in ['government', 'political', 'election', 'policy']):
                    topic_name = 'politics'
                elif any(word in top_words for word in ['movie', 'music', 'show', 'game']):
                    topic_name = 'entertainment'
                
                topics[topic_name] = float(np.mean(topic))
            
            # Normalize
            total = sum(topics.values())
            if total > 0:
                topics = {k: v/total for k, v in topics.items()}
            
            return topics
            
        except Exception as e:
            logger.error(f"LDA topic detection failed: {e}")
            return self._detect_topics_simple(" ".join(texts))
    
    def _detect_topics_simple(self, text: str) -> Dict[str, float]:
        """Simple topic detection using keyword matching"""
        topic_keywords = {
            'technology': {'tech', 'computer', 'software', 'programming', 'internet', 'web', 'app', 'digital'},
            'politics': {'government', 'election', 'political', 'policy', 'law', 'congress', 'president'},
            'entertainment': {'movie', 'music', 'game', 'show', 'video', 'film', 'tv', 'celebrity'},
            'sports': {'sport', 'team', 'player', 'game', 'match', 'football', 'basketball'},
            'business': {'business', 'money', 'economy', 'market', 'finance', 'company'},
            'health': {'health', 'medical', 'doctor', 'medicine', 'hospital', 'treatment'},
        }
        
        words = set(text.lower().split())
        topic_scores = {}
        
        for topic, keywords in topic_keywords.items():
            matches = len(words.intersection(keywords))
            if matches > 0:
                topic_scores[topic] = matches / len(keywords)
        
        # Normalize
        total = sum(topic_scores.values())
        if total > 0:
            topic_scores = {k: v/total for k, v in topic_scores.items()}
        
        return topic_scores


class ContentAnalysisManager:
    """Main manager for running content analysis tasks"""
    
    def __init__(self):
        self.settings = AnalysisSettings.get_settings()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.semantic_analyzer = SemanticAnalyzer()
    
    def should_analyze_content(self, content_item) -> bool:
        """Check if content item should be analyzed based on settings"""
        if not content_item:
            return False
        
        # Check content length
        text = self._get_content_text(content_item)
        if len(text) < self.settings.min_content_length:
            return False
        
        # Check spam status
        if self.settings.exclude_spam and hasattr(content_item, 'is_potentially_spam'):
            if content_item.is_potentially_spam:
                return False
        
        # Check age
        content_date = getattr(content_item, 'date_posted', None) or getattr(content_item, 'created_on', None)
        if content_date:
            age_limit = timezone.now() - timedelta(days=self.settings.max_content_age_days)
            if content_date < age_limit:
                return False
        
        return True
    
    def _get_content_text(self, content_item) -> str:
        """Extract text content from post or comment"""
        if hasattr(content_item, 'title') and hasattr(content_item, 'content'):
            # Post
            return f"{content_item.title} {content_item.content or ''}".strip()
        elif hasattr(content_item, 'content'):
            # Comment
            return content_item.content or ""
        return ""
    
    def analyze_sentiment_batch(self, max_items: Optional[int] = None) -> int:
        """
        Analyze sentiment for a batch of unanalyzed content
        Returns number of items processed
        """
        if not self.settings.sentiment_analysis_enabled:
            return 0
        
        max_items = max_items or self.settings.max_items_per_batch
        processed_count = 0
        
        # Get content types
        post_content_type = ContentType.objects.get_for_model(Post)
        comment_content_type = ContentType.objects.get_for_model(Comment)
        
        # Find unanalyzed posts
        analyzed_post_ids = SentimentAnalysis.objects.filter(
            content_type=post_content_type
        ).values_list('object_id', flat=True)
        
        unanalyzed_posts = Post.objects.exclude(
            id__in=analyzed_post_ids
        ).order_by('-date_posted')[:max_items//2]
        
        for post in unanalyzed_posts:
            if not self.should_analyze_content(post):
                continue
            
            text = self._get_content_text(post)
            analysis_result = self.sentiment_analyzer.analyze_sentiment(text)
            
            SentimentAnalysis.objects.update_or_create(
                content_type=post_content_type,
                object_id=post.id,
                defaults=analysis_result
            )
            
            processed_count += 1
        
        # Find unanalyzed comments
        remaining_items = max_items - processed_count
        if remaining_items > 0:
            analyzed_comment_ids = SentimentAnalysis.objects.filter(
                content_type=comment_content_type
            ).values_list('object_id', flat=True)
            
            unanalyzed_comments = Comment.objects.exclude(
                id__in=analyzed_comment_ids
            ).order_by('-created_on')[:remaining_items]
            
            for comment in unanalyzed_comments:
                if not self.should_analyze_content(comment):
                    continue
                
                text = self._get_content_text(comment)
                analysis_result = self.sentiment_analyzer.analyze_sentiment(text)
                
                SentimentAnalysis.objects.update_or_create(
                    content_type=comment_content_type,
                    object_id=comment.id,
                    defaults=analysis_result
                )
                
                processed_count += 1
        
        logger.info(f"Analyzed sentiment for {processed_count} items")
        return processed_count
    
    def generate_semantic_analysis(self, period_type: str = 'hour') -> bool:
        """
        Generate semantic analysis for a time period
        Returns True if analysis was completed
        """
        if not self.settings.semantic_analysis_enabled:
            return False
        
        now = timezone.now()
        
        if period_type == 'hour':
            period_start = now.replace(minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(hours=1)
        elif period_type == 'day':
            period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(days=1)
        elif period_type == 'week':
            days_since_monday = now.weekday()
            period_start = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(weeks=1)
        else:
            return False
        
        # Check if analysis already exists
        if SemanticAnalysis.objects.filter(period_type=period_type, period_start=period_start).exists():
            return True
        
        # Get content for the period
        posts = Post.objects.filter(date_posted__gte=period_start, date_posted__lt=period_end)
        comments = Comment.objects.filter(created_on__gte=period_start, created_on__lt=period_end)
        
        if not posts.exists() and not comments.exists():
            return False
        
        # Collect all text content
        all_text = ""
        total_posts = posts.count()
        total_comments = comments.count()
        
        post_lengths = []
        comment_lengths = []
        
        for post in posts:
            text = self._get_content_text(post)
            all_text += " " + text
            post_lengths.append(len(text))
        
        for comment in comments:
            text = self._get_content_text(comment)
            all_text += " " + text
            comment_lengths.append(len(text))
        
        # Generate semantic analysis
        keywords = self.semantic_analyzer.extract_keywords(all_text)
        topics = self.semantic_analyzer.detect_topics(all_text)
        
        # Calculate sentiment aggregates
        post_content_type = ContentType.objects.get_for_model(Post)
        comment_content_type = ContentType.objects.get_for_model(Comment)
        
        post_sentiments = SentimentAnalysis.objects.filter(
            content_type=post_content_type,
            object_id__in=posts.values_list('id', flat=True)
        ).values_list('sentiment_score', flat=True)
        
        comment_sentiments = SentimentAnalysis.objects.filter(
            content_type=comment_content_type,
            object_id__in=comments.values_list('id', flat=True)
        ).values_list('sentiment_score', flat=True)
        
        all_sentiments = list(post_sentiments) + list(comment_sentiments)
        
        avg_sentiment = sum(all_sentiments) / len(all_sentiments) if all_sentiments else 0.0
        sentiment_variance = sum((s - avg_sentiment) ** 2 for s in all_sentiments) / len(all_sentiments) if all_sentiments else 0.0
        
        # Create semantic analysis record
        SemanticAnalysis.objects.create(
            period_type=period_type,
            period_start=period_start,
            topic_distribution=topics,
            keyword_frequency=keywords,
            total_posts=total_posts,
            total_comments=total_comments,
            avg_post_length=sum(post_lengths) / len(post_lengths) if post_lengths else 0.0,
            avg_comment_length=sum(comment_lengths) / len(comment_lengths) if comment_lengths else 0.0,
            avg_sentiment=avg_sentiment,
            sentiment_variance=sentiment_variance
        )
        
        logger.info(f"Generated {period_type} semantic analysis for {period_start}")
        return True
    
    def run_full_analysis(self) -> Dict[str, int]:
        """
        Run complete analysis cycle
        Returns dict with counts of processed items
        """
        results = {
            'sentiment_analyzed': 0,
            'semantic_periods_generated': 0
        }
        
        # Run sentiment analysis
        if self.settings.sentiment_analysis_enabled:
            results['sentiment_analyzed'] = self.analyze_sentiment_batch()
        
        # Run semantic analysis for different periods
        if self.settings.semantic_analysis_enabled:
            for period_type in ['hour', 'day', 'week']:
                if self.generate_semantic_analysis(period_type):
                    results['semantic_periods_generated'] += 1
        
        return results
