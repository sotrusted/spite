from django.test import TestCase
from django.core.cache import cache
from blog.models import Post, Comment
from spite.tasks import cache_posts_data
from spite.context_processors import get_cached_posts, get_optimized_posts
from datetime import datetime, timedelta
import pickle
import lz4.frame as lz4
from unittest.mock import patch


class TestCacheFunctionality(TestCase):
    def setUp(self):
        """Set up test data"""
        cache.clear()
        
        # Create test posts
        self.pinned_post = Post.objects.create(
            title="Pinned Post",
            content="This is a pinned post",
            display_name="Test User",
            is_pinned=True,
            spam_score=10,
            date_posted=datetime.now() - timedelta(hours=1)
        )
        
        # Create regular posts
        for i in range(25):
            Post.objects.create(
                title=f"Regular Post {i}",
                content=f"Content for post {i}",
                display_name="Test User",
                is_pinned=False,
                spam_score=10,
                date_posted=datetime.now() - timedelta(hours=i+2)
            )
        
        # Create spam posts
        for i in range(5):
            Post.objects.create(
                title=f"Spam Post {i}",
                content="Spam content",
                display_name="Spammer",
                is_pinned=False,
                spam_score=80,
                date_posted=datetime.now() - timedelta(hours=i+30)
            )

    def test_cache_posts_data_task(self):
        """Test that cache_posts_data task properly caches data"""
        # Run the task
        cache_posts_data()
        
        # Check that cache keys exist
        self.assertIsNotNone(cache.get('posts_chunk_count'))
        self.assertIsNotNone(cache.get('last_cache_update'))
        self.assertIsNotNone(cache.get('total_posts_comments'))
        
        # Check chunk count
        chunk_count = cache.get('posts_chunk_count')
        self.assertGreater(chunk_count, 0)
        
        # Check that chunks exist
        for i in range(chunk_count):
            chunk_key = f'posts_chunk_{i}'
            self.assertIsNotNone(cache.get(chunk_key), f"Chunk {i} not found in cache")

    def test_cache_posts_data_spam_filtering(self):
        """Test that cache_posts_data properly filters spam"""
        cache_posts_data()
        
        chunk_count = cache.get('posts_chunk_count')
        all_posts = []
        
        # Collect all posts from cache
        for i in range(chunk_count):
            compressed_chunk = cache.get(f'posts_chunk_{i}')
            if compressed_chunk:
                chunk = pickle.loads(lz4.decompress(compressed_chunk))
                all_posts.extend(chunk)
        
        # Check pinned posts
        compressed_pinned = cache.get('pinned_posts')
        if compressed_pinned:
            pinned_posts = pickle.loads(lz4.decompress(compressed_pinned))
            all_posts.extend(pinned_posts)
        
        # Verify no spam posts in cache
        for post in all_posts:
            self.assertLess(post['spam_score'], 50, f"Spam post found in cache: {post['title']}")

    def test_cache_timestamp_setting(self):
        """Test that cache timestamp is properly set"""
        cache_posts_data()
        
        timestamp = cache.get('last_cache_update')
        self.assertIsNotNone(timestamp)
        
        # Should be recent (within last minute)
        current_time = datetime.now().timestamp()
        self.assertLess(current_time - timestamp, 60)

    def test_cache_total_count(self):
        """Test that total count is cached"""
        cache_posts_data()
        
        total_count = cache.get('total_posts_comments')
        self.assertIsNotNone(total_count)
        self.assertIsInstance(total_count, int)
        self.assertGreater(total_count, 0)

    def test_get_cached_posts_with_fresh_cache(self):
        """Test get_cached_posts with fresh cache"""
        # First cache the data
        cache_posts_data()
        
        # Then test retrieval
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/')
        
        result = get_cached_posts(request)
        
        self.assertIn('posts', result)
        self.assertIn('pinned_posts', result)
        self.assertIn('total_chunks', result)
        
        # Should have posts
        self.assertGreater(len(result['posts']), 0)
        self.assertGreater(len(result['pinned_posts']), 0)

    def test_get_cached_posts_with_stale_cache(self):
        """Test get_cached_posts with stale cache"""
        # Create stale cache
        old_timestamp = datetime.now().timestamp() - 700  # 11+ minutes old
        cache.set('last_cache_update', old_timestamp, 300)
        
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/')
        
        result = get_cached_posts(request)
        
        # Should still return data (fallback to database)
        self.assertIn('posts', result)
        self.assertIn('pinned_posts', result)

    def test_get_optimized_posts(self):
        """Test get_optimized_posts function"""
        # Cache some data first
        cache_posts_data()
        
        result = get_optimized_posts()
        
        self.assertIn('posts', result)
        self.assertIn('pinned_posts', result)
        self.assertIn('has_more', result)
        
        # Should have posts
        self.assertGreater(len(result['posts']), 0)

    def test_cache_compression(self):
        """Test that cache data is properly compressed"""
        cache_posts_data()
        
        chunk_count = cache.get('posts_chunk_count')
        
        # Check that chunks are compressed
        for i in range(min(chunk_count, 3)):  # Check first 3 chunks
            compressed_chunk = cache.get(f'posts_chunk_{i}')
            self.assertIsNotNone(compressed_chunk)
            
            # Should be able to decompress
            try:
                chunk = pickle.loads(lz4.decompress(compressed_chunk))
                self.assertIsInstance(chunk, list)
                self.assertGreater(len(chunk), 0)
            except Exception as e:
                self.fail(f"Failed to decompress chunk {i}: {e}")

    def test_cache_error_handling(self):
        """Test cache error handling"""
        # Test with corrupted cache
        cache.set('posts_chunk_0', b'corrupted_data', 300)
        cache.set('posts_chunk_count', 1, 300)
        
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/')
        
        # Should not raise exception, should fall back gracefully
        result = get_cached_posts(request)
        self.assertIn('posts', result)

    def test_cache_expiration(self):
        """Test that cache expires properly"""
        # Set cache with short expiration
        cache.set('last_cache_update', datetime.now().timestamp(), 1)
        
        # Wait for expiration (in real scenario, this would be handled by cache backend)
        # For testing, we'll manually check the behavior
        
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/')
        
        # Should handle missing cache gracefully
        cache.delete('last_cache_update')
        result = get_cached_posts(request)
        self.assertIn('posts', result)

    def test_concurrent_cache_access(self):
        """Test that cache can handle concurrent access"""
        # This is more of a smoke test
        cache_posts_data()
        
        from django.test import RequestFactory
        factory = RequestFactory()
        
        # Simulate multiple requests
        results = []
        for i in range(5):
            request = factory.get(f'/?page={i+1}')
            result = get_cached_posts(request)
            results.append(result)
        
        # All should succeed
        for result in results:
            self.assertIn('posts', result)
            self.assertIn('pinned_posts', result)

    def tearDown(self):
        """Clean up after tests"""
        cache.clear()
