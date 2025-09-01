from django.core.management.base import BaseCommand
from blog.models import Post, Comment
from django.core.cache import cache
import logging
from difflib import SequenceMatcher

logger = logging.getLogger('spite')

class Command(BaseCommand):
    help = 'Retroactively score the most recent 100 posts/comments without spam scores'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Number of posts/comments to process (default: 100)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without actually updating',
        )
        parser.add_argument(
            '--posts-only',
            action='store_true',
            help='Only process posts, not comments',
        )
        parser.add_argument(
            '--comments-only',
            action='store_true',
            help='Only process comments, not posts',
        )
        parser.add_argument(
            '--status',
            action='store_true',
            help='Show current spam scoring status without processing anything',
        )

    def handle(self, *args, **options):
        limit = options['limit']
        dry_run = options['dry_run']
        posts_only = options['posts_only']
        comments_only = options['comments_only']
        status = options['status']
        
        if status:
            self.show_status()
            return
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN - No posts/comments will be updated')
            )
        
        total_processed = 0
        total_spam_found = 0
        
        # Process posts
        if not comments_only:
            posts_processed, posts_spam = self.process_posts(limit, dry_run)
            total_processed += posts_processed
            total_spam_found += posts_spam
            
            self.stdout.write(
                self.style.SUCCESS(f'Posts: {posts_processed} processed, {posts_spam} marked as spam')
            )
        
        # Process comments
        if not posts_only:
            comments_processed, comments_spam = self.process_comments(limit, dry_run)
            total_processed += comments_processed
            total_spam_found += comments_spam
            
            self.stdout.write(
                self.style.SUCCESS(f'Comments: {comments_processed} processed, {comments_spam} marked as spam')
            )
        
        # Update global cache
        if not dry_run:
            self.update_global_spam_cache()
            self.stdout.write(
                self.style.SUCCESS('Updated global spam cache')
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'Total: {total_processed} items processed, {total_spam_found} marked as spam')
        )
    
    def show_status(self):
        """Show current spam scoring status"""
        total_posts = Post.objects.count()
        posts_with_spam_reasons = Post.objects.filter(spam_reasons__isnull=False).count()
        posts_without_spam_reasons = Post.objects.filter(spam_reasons__isnull=True).count()
        
        total_comments = Comment.objects.count()
        comments_with_spam_reasons = Comment.objects.filter(spam_reasons__isnull=False).count()
        comments_without_spam_reasons = Comment.objects.filter(spam_reasons__isnull=True).count()
        
        self.stdout.write('=== Spam Scoring Status ===')
        self.stdout.write(f'Posts: {total_posts} total, {posts_with_spam_reasons} processed, {posts_without_spam_reasons} unprocessed')
        self.stdout.write(f'Comments: {total_comments} total, {comments_with_spam_reasons} processed, {comments_without_spam_reasons} unprocessed')
        
        # Show some examples of unprocessed items
        if posts_without_spam_reasons > 0:
            self.stdout.write('\n=== Sample Unprocessed Posts ===')
            sample_posts = Post.objects.filter(spam_reasons__isnull=True).order_by('-date_posted')[:3]
            for post in sample_posts:
                self.stdout.write(f'  Post {post.id}: "{post.title[:50]}..." (created: {post.date_posted})')
        
        if comments_without_spam_reasons > 0:
            self.stdout.write('\n=== Sample Unprocessed Comments ===')
            sample_comments = Comment.objects.filter(spam_reasons__isnull=True).order_by('-created_on')[:3]
            for comment in sample_comments:
                self.stdout.write(f'  Comment {comment.id}: "{comment.content[:50]}..." (created: {comment.created_on})')
        
        # Show some examples of processed items
        if posts_with_spam_reasons > 0:
            self.stdout.write('\n=== Sample Processed Posts ===')
            sample_posts = Post.objects.filter(spam_reasons__isnull=False).order_by('-date_posted')[:3]
            for post in sample_posts:
                self.stdout.write(f'  Post {post.id}: Score {post.spam_score}, Reasons: {post.spam_reasons[:50]}...')
        
        if comments_with_spam_reasons > 0:
            self.stdout.write('\n=== Sample Processed Comments ===')
            sample_comments = Comment.objects.filter(spam_reasons__isnull=False).order_by('-created_on')[:3]
            for comment in sample_comments:
                self.stdout.write(f'  Comment {comment.id}: Score {comment.spam_score}, Reasons: {comment.spam_reasons[:50]}...')
    
    def process_posts(self, limit, dry_run):
        """Process posts without spam scores"""
        # Check for posts that either have no spam_score field or have never been processed
        # Since spam_score defaults to 0, we need to check if spam_reasons is empty
        posts = Post.objects.filter(
            spam_reasons__isnull=True
        ).order_by('-date_posted')[:limit]
        
        processed = 0
        spam_found = 0
        
        for post in posts:
            try:
                spam_score, spam_reasons = self.calculate_spam_score_for_post(post)
                
                if dry_run:
                    if spam_score > 0:
                        self.stdout.write(f'[DRY RUN] Post {post.id} would get spam score {spam_score}: {spam_reasons}')
                        spam_found += 1
                else:
                    if spam_score > 0:
                        post.spam_score = spam_score
                        post.spam_reasons = '; '.join(spam_reasons)
                        spam_found += 1
                    else:
                        post.spam_score = 0
                        post.spam_reasons = 'No spam detected'
                    
                    post.save(update_fields=['spam_score', 'spam_reasons'])
                
                processed += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error processing post {post.id}: {e}')
                )
                continue
        
        return processed, spam_found
    
    def process_comments(self, limit, dry_run):
        """Process comments without spam scores"""
        # Check for comments that either have no spam_score field or have never been processed
        # Since spam_score defaults to 0, we need to check if spam_reasons is empty
        comments = Comment.objects.filter(
            spam_reasons__isnull=True
        ).order_by('-created_on')[:limit]
        
        processed = 0
        spam_found = 0
        
        for comment in comments:
            try:
                spam_score, spam_reasons = self.calculate_spam_score_for_comment(comment)
                
                if dry_run:
                    if spam_score > 0:
                        self.stdout.write(f'[DRY RUN] Comment {comment.id} would get spam score {spam_score}: {spam_reasons}')
                        spam_found += 1
                else:
                    if spam_score > 0:
                        comment.spam_score = spam_score
                        comment.spam_reasons = '; '.join(spam_reasons)
                        spam_found += 1
                    else:
                        comment.spam_score = 0
                        comment.spam_reasons = 'No spam detected'
                    
                    comment.save(update_fields=['spam_score', 'spam_reasons'])
                
                processed += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error processing comment {comment.id}: {e}')
                )
                continue
        
        return processed, spam_found
    
    def calculate_spam_score_for_post(self, post):
        """Calculate spam score for a single post"""
        spam_score = 0
        spam_reasons = []
        
        # Create content string
        content = f"{post.title.lower().strip() if post.title else ''} {post.content.lower().strip() if post.content else ''} {post.display_name.lower().strip() if post.display_name else ''}"
        content = ' '.join(content.split())
        
        # Check for excessive word repetition
        words = content.split()
        if len(words) > 10:
            word_counts = {}
            for word in words:
                if len(word) > 3:
                    word_counts[word] = word_counts.get(word, 0) + 1
            
            for word, count in word_counts.items():
                if count > len(words) * 0.4:
                    spam_score += 40
                    spam_reasons.append(f"Excessive repetition of '{word}'")
                    break
        
        # Check for repetitive patterns
        if len(content) > 100:
            # Look for repeated phrases
            for seq_len in range(5, min(10, len(words)//2)):
                for i in range(len(words) - seq_len + 1):
                    sequence = ' '.join(words[i:i+seq_len])
                    if len(sequence) > 20:
                        count = content.count(sequence)
                        if count >= 3:
                            spam_score += 50
                            spam_reasons.append(f"Repeated phrase: '{sequence[:50]}...'")
                            break
                if spam_score >= 50:
                    break
        
        return spam_score, spam_reasons
    
    def calculate_spam_score_for_comment(self, comment):
        """Calculate spam score for a single comment"""
        spam_score = 0
        spam_reasons = []
        
        # Create content string
        content = f"{comment.name.lower().strip() if comment.name else ''} {comment.content.lower().strip() if comment.content else ''}"
        content = ' '.join(content.split())
        
        # Check for excessive word repetition
        words = content.split()
        if len(words) > 10:
            word_counts = {}
            for word in words:
                if len(word) > 3:
                    word_counts[word] = word_counts.get(word, 0) + 1
            
            for word, count in word_counts.items():
                if count > len(words) * 0.4:
                    spam_score += 40
                    spam_reasons.append(f"Excessive repetition of '{word}'")
                    break
        
        # Check for repetitive patterns
        if len(content) > 100:
            for seq_len in range(5, min(10, len(words)//2)):
                for i in range(len(words) - seq_len + 1):
                    sequence = ' '.join(words[i:i+seq_len])
                    if len(sequence) > 20:
                        count = content.count(sequence)
                        if count >= 3:
                            spam_score += 50
                            spam_reasons.append(f"Repeated phrase: '{sequence[:50]}...'")
                            break
                if spam_score >= 50:
                    break
        
        return spam_score, spam_reasons
    
    def update_global_spam_cache(self):
        """Update global spam cache with recent content"""
        try:
            # Get recent posts and comments for global cache
            recent_posts = Post.objects.order_by('-date_posted')[:50]
            recent_comments = Comment.objects.order_by('-created_on')[:50]
            
            global_content = []
            
            # Add post content
            for post in recent_posts:
                content = f"{post.title.lower().strip() if post.title else ''} {post.content.lower().strip() if post.content else ''} {post.display_name.lower().strip() if post.display_name else ''}"
                content = ' '.join(content.split())
                global_content.append(content)
            
            # Add comment content
            for comment in recent_comments:
                content = f"{comment.name.lower().strip() if comment.name else ''} {comment.content.lower().strip() if comment.content else ''}"
                content = ' '.join(content.split())
                global_content.append(content)
            
            # Update cache
            cache.set('global_recent_posts_fast', global_content, 600)
            logger.info(f"Updated global spam cache with {len(global_content)} items")
            
        except Exception as e:
            logger.error(f"Error updating global spam cache: {e}") 