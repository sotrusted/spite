from django.test import TestCase, RequestFactory
from django.core.cache import cache
from django.contrib.auth.models import User
from blog.models import Post, Comment
from spite.context_processors import (
    get_cached_posts, 
    get_database_fallback, 
    load_posts,
    DictToObject,
    get_optimized_posts
)
from datetime import datetime, timedelta
import pickle
import lz4.frame as lz4


class TestContextProcessors(TestCase):
    def setUp(self):
        """Set up test data"""
        self.factory = RequestFactory()
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
        
        self.regular_posts = []
        for i in range(25):  # Create 25 regular posts
            post = Post.objects.create(
                title=f"Regular Post {i}",
                content=f"Content for post {i}",
                display_name="Test User",
                is_pinned=False,
                spam_score=10,
                date_posted=datetime.now() - timedelta(hours=i+2)
            )
            self.regular_posts.append(post)
        
        # Create spam posts (should be filtered out)
        for i in range(5):
            Post.objects.create(
                title=f"Spam Post {i}",
                content="Spam content",
                display_name="Spammer",
                is_pinned=False,
                spam_score=80,  # High spam score
                date_posted=datetime.now() - timedelta(hours=i+30)
            )
        
        # Create comments for some posts
        for i, post in enumerate(self.regular_posts[:10]):
            for j in range(3):  # 3 comments per post
                Comment.objects.create(
                    post=post,
                    name=f"Commenter {i}-{j}",
                    content=f"Comment {j} for post {i}",
                    spam_score=10,
                    created_on=datetime.now() - timedelta(minutes=j*10)
                )

    def test_dict_to_object_conversion(self):
        """Test DictToObject properly converts dictionaries to objects"""
        test_data = {
            'id': 1,
            'title': 'Test Post',
            'content': 'Test content',
            'media_file': 'test.jpg',
            'is_pinned': False
        }
        
        obj = DictToObject(test_data)
        
        self.assertEqual(obj.id, 1)
        self.assertEqual(obj.title, 'Test Post')
        self.assertEqual(obj.content, 'Test content')
        self.assertEqual(obj.is_pinned, False)
        self.assertTrue(hasattr(obj, 'media_file'))
        self.assertEqual(obj.get_item_type(), 'Post')

    def test_database_fallback_loads_all_posts(self):
        """Test that database fallback loads all posts, not just limited subset"""
        result = get_database_fallback()
        
        # Should load all regular posts (25) and 1 pinned post
        self.assertEqual(len(result['posts']), 25)
        self.assertEqual(len(result['pinned_posts']), 1)
        self.assertEqual(result['total_chunks'], 0)
        
        # Check that spam posts are filtered out
        for post in result['posts']:
            self.assertLess(post.spam_score, 50)
        
        for post in result['pinned_posts']:
            self.assertLess(post.spam_score, 50)

    def test_database_fallback_post_attributes(self):
        """Test that database fallback posts have all required attributes"""
        result = get_database_fallback()
        
        if result['posts']:
            post = result['posts'][0]
            required_attrs = [
                'id', 'title', 'content', 'display_name', 'date_posted',
                'is_pinned', 'media_file', 'image', 'anon_uuid', 'parent_post',
                'is_image', 'is_video', 'spam_score'
            ]
            
            for attr in required_attrs:
                self.assertTrue(hasattr(post, attr), f"Post missing attribute: {attr}")

    def test_cached_posts_with_fresh_cache(self):
        """Test get_cached_posts when cache is fresh"""
        # Manually create cache data
        posts_data = [
            {
                'id': 1,
                'title': 'Cached Post',
                'content': 'Cached content',
                'display_name': 'Cached User',
                'date_posted': datetime.now(),
                'is_pinned': False,
                'media_file': None,
                'image': None,
                'anon_uuid': 'test-uuid',
                'parent_post': None,
                'is_image': False,
                'is_video': False,
                'spam_score': 10
            }
        ]
        
        # Cache the data
        compressed = lz4.compress(pickle.dumps(posts_data))
        cache.set('posts_chunk_0', compressed, 300)
        cache.set('posts_chunk_count', 1, 300)
        cache.set('last_cache_update', datetime.now().timestamp(), 300)
        
        request = self.factory.get('/')
        result = get_cached_posts(request)
        
        self.assertEqual(len(result['posts']), 1)
        self.assertEqual(result['posts'][0].title, 'Cached Post')
        self.assertEqual(result['total_chunks'], 1)

    def test_cached_posts_with_stale_cache(self):
        """Test get_cached_posts when cache is stale"""
        # Create stale cache
        old_timestamp = datetime.now().timestamp() - 700  # 11+ minutes old
        cache.set('last_cache_update', old_timestamp, 300)
        
        request = self.factory.get('/')
        result = get_cached_posts(request)
        
        # Should fall back to database
        self.assertGreater(len(result['posts']), 0)
        self.assertEqual(result['total_chunks'], 0)

    def test_load_posts_pagination(self):
        """Test that load_posts properly handles pagination"""
        request = self.factory.get('/?page=1')
        context = load_posts(request)
        
        # Should have posts in context
        self.assertIn('posts', context)
        self.assertIn('pinned_posts', context)
        
        # Check pagination
        posts = context['posts']
        self.assertTrue(hasattr(posts, 'has_other_pages'))
        self.assertTrue(hasattr(posts, 'number'))
        self.assertTrue(hasattr(posts, 'paginator'))
        
        # First page should have posts
        self.assertGreater(len(posts.object_list), 0)

    def test_load_posts_page_2(self):
        """Test pagination on page 2"""
        request = self.factory.get('/?page=2')
        context = load_posts(request)
        
        posts = context['posts']
        self.assertEqual(posts.number, 2)
        
        # Should still have posts on page 2
        if posts.has_other_pages():
            self.assertGreater(len(posts.object_list), 0)

    def test_load_posts_post_attributes(self):
        """Test that posts in load_posts have all required attributes"""
        request = self.factory.get('/')
        context = load_posts(request)
        
        if context['posts'].object_list:
            post = context['posts'].object_list[0]
            
            # Check basic attributes
            self.assertTrue(hasattr(post, 'id'))
            self.assertTrue(hasattr(post, 'title'))
            self.assertTrue(hasattr(post, 'content'))
            self.assertTrue(hasattr(post, 'display_name'))
            self.assertTrue(hasattr(post, 'date_posted'))
            
            # Check comment-related attributes (should be added by batch loading)
            if hasattr(post, 'get_item_type') and post.get_item_type() == 'Post':
                self.assertTrue(hasattr(post, 'comments_total'))
                self.assertTrue(hasattr(post, 'recent_comments'))

    def test_load_posts_comment_loading(self):
        """Test that comments are properly loaded for posts"""
        request = self.factory.get('/')
        context = load_posts(request)
        
        # Find a post that should have comments
        posts_with_comments = [
            post for post in context['posts'].object_list 
            if hasattr(post, 'get_item_type') and post.get_item_type() == 'Post'
        ]
        
        if posts_with_comments:
            post = posts_with_comments[0]
            
            # Should have comment attributes
            self.assertTrue(hasattr(post, 'comments_total'))
            self.assertTrue(hasattr(post, 'recent_comments'))
            
            # comments_total should be an integer
            self.assertIsInstance(post.comments_total, int)
            
            # recent_comments should be a list
            self.assertIsInstance(post.recent_comments, list)

    def test_load_posts_context_variables(self):
        """Test that all required context variables are present"""
        request = self.factory.get('/')
        context = load_posts(request)
        
        required_vars = [
            'days_since_launch',
            'comment_form',
            'search_form',
            'postForm',
            'posts',
            'pinned_posts',
            'spite',
            'is_paginated',
            'highlight_comments',
            'is_loading'
        ]
        
        for var in required_vars:
            self.assertIn(var, context, f"Missing context variable: {var}")

    def test_spam_filtering(self):
        """Test that spam posts are properly filtered out"""
        request = self.factory.get('/')
        context = load_posts(request)
        
        # Check regular posts
        for post in context['posts'].object_list:
            if hasattr(post, 'spam_score'):
                self.assertLess(post.spam_score, 50, "Spam post found in regular posts")
        
        # Check pinned posts
        for post in context['pinned_posts']:
            if hasattr(post, 'spam_score'):
                self.assertLess(post.spam_score, 50, "Spam post found in pinned posts")

    def test_performance_optimizations(self):
        """Test that performance optimizations don't break functionality"""
        request = self.factory.get('/')
        
        # This should not raise any exceptions
        context = load_posts(request)
        
        # Should have posts
        self.assertGreater(len(context['posts'].object_list), 0)
        
        # Should have proper pagination
        self.assertTrue(hasattr(context['posts'], 'has_other_pages'))
        
        # Should have cached count
        self.assertIsInstance(context['spite'], int)
        self.assertGreater(context['spite'], 0)

    def tearDown(self):
        """Clean up after tests"""
        cache.clear()
