from django.shortcuts import redirect, render, get_object_or_404
from itertools import chain
from django.db.models import Prefetch
from django.core.files.storage import default_storage
from django.utils.html import escape
from crispy_forms.templatetags.crispy_forms_filters import as_crispy_form
from django.views.decorators.cache import never_cache
from django.middleware.csrf import get_token
from django.http import JsonResponse
from django.utils.timezone import localtime, now
from django.urls import reverse_lazy, reverse
from django.core.cache import cache
from django.db.models import Q
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.core.files.uploadhandler import TemporaryFileUploadHandler
from django.views.decorators.cache import cache_page
import logging
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
import os
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.generic import CreateView, DetailView, ListView
from django.views import View
from blog.models import Post, Comment, SearchQueryLog, PageView, List, SecureIPStorage
from django.contrib import messages
from blog.forms import PostForm, ReplyForm, CommentForm
import functools
from datetime import datetime, timedelta
from spite.context_processors import get_posts, get_optimized_posts, get_cached_posts
from django.http import StreamingHttpResponse
from weasyprint import HTML
import cv2
import numpy as np
from django.conf import settings
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from difflib import SequenceMatcher
import hashlib
import lz4
import pickle
import time
import requests
from django.db import connection
from contextlib import contextmanager

logger = logging.getLogger('spite')

def check_spam(request, content='', author_name=''):
    logger.info("Checking spam")
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    logger.info(f"Client IP: {client_ip}")


    # 1. Rate limiting
    cache_key = f'post_count_{client_ip}'
    post_count = cache.get(cache_key, 0)
    
    if post_count > 5:  # Max 5 posts per minute
        return True, "Please wait a minute before posting again"
    
    # Increment post count
    cache.set(cache_key, post_count + 1, 60)  # Expires in 60 seconds
    
    # 2. Check recent posts for similar content
    recent_posts_key = f'recent_posts_{client_ip}'
    recent_posts = cache.get(recent_posts_key, [])
    logger.info(f"Recent posts: {recent_posts}")
    
    # Create content hash including name
    content_to_check = f"{content.lower().strip() if content else ''} {author_name.lower().strip() if author_name else ''}"
    content_hash = hashlib.md5(content_to_check.encode()).hexdigest()
    logger.info(f"Content to check: {content_to_check}")
    logger.info(f"Content hash: {content_hash}")
    
    # Check for duplicate or similar content
    for recent_hash in recent_posts:
        if content_hash == recent_hash:
            return True, "This looks like a duplicate post"
    
    # Check content similarity with recent posts
    for recent_post in Post.objects.filter(
        date_posted__gte=now() - timedelta(minutes=5)
    ).order_by('-date_posted')[:10]:
        similarity = SequenceMatcher(
            None,
            content_to_check,
            f"{recent_post.content.lower().strip() if recent_post.content else ''} {recent_post.display_name.lower().strip() if recent_post.display_name else ''}"
        ).ratio()
        
        logger.info(f"Similarity: {similarity}")
        if similarity > 0.8:  # 80% similarity threshold
            return True, "This content is too similar to a recent post"
    
    # Store this content hash
    recent_posts.append(content_hash)
    if len(recent_posts) > 10:  # Keep last 10 posts
        recent_posts.pop(0)
    cache.set(recent_posts_key, recent_posts, 300)  # Store for 5 minutes

    logger.info("Post is not spam")
    return False, ""

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

CACHE_KEY = 'home_cache'

@csrf_protect
def home(request):
    
    # Get the immediate total count
    total_pageviews = cache.get('current_total_views', 0)

    # Cache the IP submission status for each IP
    client_ip = get_client_ip(request)
    cache_key = f'ip_submitted_{client_ip}'
    
    ip_has_submitted = cache.get(cache_key)
    if ip_has_submitted is None:
        # Only hit the database if not in cache
        ip_has_submitted = List.objects.filter(ip_address=client_ip).exists()
        # Cache for 1 hour (3600 seconds)
        cache.set(cache_key, ip_has_submitted, 60 * 60 * 7)

    return render(request, 'blog/home.html', 
                {'pageview_count': total_pageviews,
                 'ip_has_submitted': ip_has_submitted})

def all_posts(request):
    _, posts, _ = get_posts()
    context = {'posts' : posts}
    return render(request, 'blog/all_posts.html', context=context)

class PostCreateView(CreateView):
    model = Post
    fields = ['title', 'content', 'media_file', 'display_name']
    template_name = 'blog/post_form.html'
    form_context_name = 'postForm'
    form = PostForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context[self.form_context_name] = self.form()
        return context

    def check_spam(self, request, title, content, author_name=''):
        logger.info("Checking spam")
        client_ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
        
        # 1. Rate limiting
        cache_key = f'post_count_{client_ip}'
        post_count = cache.get(cache_key, 0)
        
        if post_count > 5:  # Max 5 posts per minute
            return True, "Please wait a minute before posting again"
        
        # Increment post count
        cache.set(cache_key, post_count + 1, 60)  # Expires in 60 seconds
        
        # 2. Check recent posts for similar content (optimized for speed)

        # Use cache for recent post content hashes to avoid DB hits and expensive similarity checks
        recent_posts_key = f'recent_posts_{client_ip}'
        recent_posts = cache.get(recent_posts_key, [])

        # Create content hash including name
        content_to_check = f"{title.lower().strip() if title else ''} {content.lower().strip() if content else ''} {author_name.lower().strip() if author_name else ''}"
        content_hash = hashlib.md5(content_to_check.encode()).hexdigest()

        # Fast: Check for exact duplicate in recent hashes (O(N), N small)
        if content_hash in recent_posts:
            return True, "This looks like a duplicate post"

        # Optimization: Only check similarity if there are no exact matches
        # To further speed up, cache recent post "content_to_check" strings as well
        recent_posts_content_key = f'recent_posts_content_{client_ip}'
        recent_posts_content = cache.get(recent_posts_content_key, [])

        # Only fetch from DB if we don't have enough recent post contents cached
        if len(recent_posts_content) < 10:
            # Only fetch the fields we need for similarity
            recent_db_posts = Post.objects.filter(
                date_posted__gte=localtime() - timedelta(minutes=5)
            ).order_by('-date_posted').values_list('title', 'content', 'display_name')[:10]
            recent_posts_content = [
                f"{t.lower().strip() if t else ''} {c.lower().strip() if c else ''} {d.lower().strip() if d else ''}"
                for t, c, d in recent_db_posts
            ]
            cache.set(recent_posts_content_key, recent_posts_content, 300)  # 5 min cache

        # Use SequenceMatcher only on recent post contents (still O(N), but N is small and avoids DB hits)
        for recent_content in recent_posts_content:
            # Quick length check to skip obviously different posts
            if abs(len(content_to_check) - len(recent_content)) > 40:
                continue
            similarity = SequenceMatcher(None, content_to_check, recent_content).ratio()
            if similarity > 0.8:  # 80% similarity threshold
                return True, "This content is too similar to a recent post"

        # Store this content hash and content for future fast checks
        recent_posts.append(content_hash)
        if len(recent_posts) > 10:  # Keep last 10 posts
            recent_posts.pop(0)
        cache.set(recent_posts_key, recent_posts, 300)  # Store for 5 minutes

        recent_posts_content.append(content_to_check)
        if len(recent_posts_content) > 10:
            recent_posts_content.pop(0)
        cache.set(recent_posts_content_key, recent_posts_content, 300)
        return False, ""
    
    def get_fast_image_fingerprint(self, media_file):
        """Get a fast image fingerprint for a media file"""
        try: 
            media_file.seek(0)

            # Get file size
            media_file.seek(0,2)
            file_size = media_file.tell()

            # Read first and last 1KB for fingerprint
            media_file.seek(0)
            first_chunk = media_file.read(1024)

            if file_size > 2048:
                media_file.seek(-1024, 2)
                last_chunk = media_file.read(1024)
            else:
                last_chunk = b''
            
            media_file.seek(0) # Reset for later

            # Create fingerprint from size + first/last chunks
            fingerprint_data = f"{file_size}_{hashlib.md5(first_chunk+last_chunk).hexdigest()}"
            return fingerprint_data
            
        except Exception as e:
            logger.error(f"Error getting fast image fingerprint: {e}")
            return None

    def detect_repetitive_patterns(self, content):
        """Detect repetitive text patterns that indicate spam"""
        if not content or len(content) < 20:
            return False, ""
        
        # Normalize content
        normalized = ' '.join(content.lower().split())
        
        # Check for repeated phrases (3+ times)
        words = normalized.split()
        if len(words) < 10:
            return False, ""
        
        # Look for repeated word sequences
        for seq_len in range(3, min(8, len(words)//2)):
            for i in range(len(words) - seq_len + 1):
                sequence = ' '.join(words[i:i+seq_len])
                if len(sequence) > 15:  # Only check meaningful sequences
                    count = normalized.count(sequence)
                    if count >= 3:
                        logger.info(f"[SpamCheck] Repetitive pattern detected: '{sequence}' appears {count} times")
                        return True, "Content contains repetitive patterns"
        
        # Check for excessive repetition of individual words
        word_counts = {}
        for word in words:
            if len(word) > 3:  # Only count words longer than 3 chars
                word_counts[word] = word_counts.get(word, 0) + 1
        
        # If any word appears more than 30% of the time, it's suspicious
        for word, count in word_counts.items():
            if count > len(words) * 0.3:
                logger.info(f"[SpamCheck] Excessive word repetition: '{word}' appears {count} times in {len(words)} words")
                return True, "Content contains excessive word repetition"
        
        return False, ""
        
    def check_spam_fast(self, request, title, content, display_name, media_file=None):
        """Fast spam detection that scores content instead of blocking"""
        try:
            client_ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
            logger.info(f"[SpamCheck] Client IP: {client_ip}")
            
            spam_score = 0
            spam_reasons = []
            
            # 1. Rate limiting - still block if too aggressive
            cache_key = f'post_count_{client_ip}'
            post_count = cache.get(cache_key, 0)
            
            if post_count > 5:  # Back to 5 per minute
                logger.info(f"[SpamCheck] Rate limit exceeded for IP {client_ip}")
                return True, "Please wait a minute before posting again"
            
            # Increment post count
            cache.set(cache_key, post_count + 1, 60)
            
            # 2. Fast content checks (lightweight)
            content_to_check = f"{title.lower().strip() if title else ''} {content.lower().strip() if content else ''} {display_name.lower().strip() if display_name else ''}"
            content_to_check = ' '.join(content_to_check.split())
            
            # Quick repetitive word check (fast)
            words = content_to_check.split()
            if len(words) > 10:
                word_counts = {}
                for word in words:
                    if len(word) > 3:
                        word_counts[word] = word_counts.get(word, 0) + 1
                
                # Check for excessive repetition
                for word, count in word_counts.items():
                    if count > len(words) * 0.4:  # 40% threshold
                        spam_score += 40  # Increased from 30
                        spam_reasons.append(f"Excessive repetition of '{word}'")
                        break  # Only count once
            
            # 3. Fast global duplicate check (limited scope)
            global_key = 'global_recent_posts_fast'
            global_recent = cache.get(global_key, [])
            
            # Only check against last 20 posts for speed
            if content_to_check in global_recent[-20:]:
                spam_score += 70  # Increased from 50 - this should trigger hiding
                spam_reasons.append("Exact duplicate of recent content")
            
            # 4. IP-specific duplicate check
            recent_posts_key = f'recent_posts_{client_ip}'
            recent_posts = cache.get(recent_posts_key, [])
            
            content_hash = hashlib.md5(content_to_check.encode()).hexdigest()
            if content_hash in recent_posts:
                spam_score += 50  # Increased from 40
                spam_reasons.append("You've posted this content recently")
            
            # 5. Update caches
            global_recent.append(content_to_check)
            if len(global_recent) > 100:  # Keep more posts
                global_recent.pop(0)
            cache.set(global_key, global_recent, 600)
            
            recent_posts.append(content_hash)
            if len(recent_posts) > 10:
                recent_posts.pop(0)
            cache.set(recent_posts_key, recent_posts, 300)
            
            # 6. Image duplicate check (existing logic)
            if media_file and hasattr(media_file, 'read'):
                try:
                    fingerprint = self.get_fast_image_fingerprint(media_file)
                    if fingerprint: 
                        recent_images_key = f'global_recent_images'
                        recent_images = cache.get(recent_images_key, [])
                        
                        for recent_fingerprint in recent_images:
                            if recent_fingerprint['fingerprint'] == fingerprint:
                                spam_score += 60
                                spam_reasons.append("This image has been posted recently")
                                break

                        image_data = {
                            'fingerprint': fingerprint,
                            'timestamp': time.time(),
                        }
                        
                        recent_images.append(image_data)
                        current_time = time.time()
                        filtered_images = [
                            img for img in recent_images[-100:]
                            if current_time - img['timestamp'] < 1800
                        ]
                        cache.set(recent_images_key, filtered_images, 1800)

                except Exception as e:
                    logger.warning(f"Error checking image duplicate: {e}")
            
            # 7. Determine action based on score
            if spam_score >= 80:  # High spam score - block
                logger.info(f"[SpamCheck] High spam score {spam_score} for IP {client_ip}: {spam_reasons}")
                return True, f"Content flagged as spam: {'; '.join(spam_reasons)}"
            elif spam_score >= 50:  # Medium-high spam score - allow but mark (will be hidden)
                logger.info(f"[SpamCheck] Medium-high spam score {spam_score} for IP {client_ip}: {spam_reasons}")
                # Store spam score in request for later use
                request.spam_score = spam_score
                request.spam_reasons = spam_reasons
                return False, ""  # Allow the post but it will be hidden
            elif spam_score >= 30:  # Medium spam score - allow but push down
                logger.info(f"[SpamCheck] Medium spam score {spam_score} for IP {client_ip}: {spam_reasons}")
                # Store spam score in request for later use
                request.spam_score = spam_score
                request.spam_reasons = spam_reasons
                return False, ""  # Allow the post, will be pushed down
            else:  # Low spam score - normal post
                logger.info(f"[SpamCheck] Low spam score {spam_score} for IP {client_ip}")
                return False, ""
            
        except Exception as e:
            logger.error(f"[SpamCheck] Error in spam check: {e}", exc_info=True)
            return False, ""

    def clear_spam_caches(self):
        """Clear all spam-related caches - useful for maintenance"""
        try:
            # Clear global content cache
            cache.delete('global_recent_posts_fast')
            # Clear global image cache
            cache.delete('global_recent_images')
            # Clear all IP-specific caches (this is more aggressive)
            # Note: In production, you might want to be more selective
            logger.info("[SpamCheck] Cleared all spam caches")
        except Exception as e:
            logger.error(f"[SpamCheck] Error clearing caches: {e}")

    def get_spam_stats(self):
        """Get statistics about current spam detection state"""
        try:
            global_posts = cache.get('global_recent_posts_fast', [])
            global_images = cache.get('global_recent_images', [])
            
            stats = {
                'global_posts_count': len(global_posts),
                'global_images_count': len(global_images),
                'cache_keys': [
                    'global_recent_posts_fast',
                    'global_recent_images'
                ]
            }
            
            # Count IP-specific caches
            ip_caches = 0
            for key in cache.keys('*'):
                if key.startswith('post_count_') or key.startswith('recent_posts_'):
                    ip_caches += 1
            
            stats['ip_caches_count'] = ip_caches
            return stats
            
        except Exception as e:
            logger.error(f"[SpamCheck] Error getting spam stats: {e}")
            return {'error': str(e)}



    def post(self, request, *args, **kwargs):
        try:
            logger.info(f"PostCreateView.post called with method: {request.method}")
            logger.info(f"Request headers: {dict(request.headers)}")
            logger.info(f"Request POST data: {request.POST}")
            logger.info(f"Request FILES data: {request.FILES}")
            
            # Let Django handle CSRF validation automatically
            # Remove custom CSRF validation that's causing issues
            
            self.request = request
            logger.info("Calling super().post()")
            result = super().post(request, *args, **kwargs)
            logger.info(f"super().post() returned: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error in PostCreateView.post: {e}", exc_info=True)
            if request.headers.get('HX-Request'):
                return HttpResponse(
                    f"<div class='alert alert-danger'>Server error: {str(e)}</div>",
                    status=500
                )
            messages.error(request, f"Server error: {str(e)}")
            return self.form_invalid(self.get_form())
    
    def form_valid(self, form):
        logger.info("PostCreateView.form_valid called")
        logger.info("Form submitted successfully via %s", self.request.headers.get('x-requested-with'))
        logger.info(f"Form data: {form.cleaned_data}")
        logger.info(f"Request headers: {dict(self.request.headers)}")
        
        try:
            logger.info("Form is valid, proceeding to save")
            # Save the form and get the post instance
            post = form.save(commit=False)
            logger.info(f"Post instance created: title='{post.title}', content='{post.content}', display_name='{post.display_name}'")
            
            # Add IP address to the post
            ip_address = self.request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or \
                            self.request.META.get('REMOTE_ADDR')
            logger.info(f"IP address: {ip_address}")
            
            logger.info("Checking for spam")
            is_spam, spam_message = self.check_spam_fast(
                self.request,
                post.title,
                post.content,
                post.display_name,
                media_file=post.media_file  # This is the uploaded file object
            )
            logger.info(f"Spam check result: is_spam={is_spam}, message='{spam_message}'")
            
            if is_spam:
                logger.warning(f"Spam detected: {spam_message}")
                if self.request.headers.get('HX-Request'):
                    return HttpResponse(
                        f"<div class='alert alert-danger'>{spam_message}</div>",
                        status=400
                    )
                if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False, 
                        'error': spam_message
                    }, status=400)
                messages.error(self.request, spam_message)
                return self.form_invalid(form)

            # Store spam score and reasons if they exist
            spam_score = getattr(self.request, 'spam_score', 0)
            spam_reasons = getattr(self.request, 'spam_reasons', [])
            
            if spam_score > 0:
                logger.info(f"Post has spam score {spam_score}: {spam_reasons}")
                # Store spam metadata with the post
                post.spam_score = spam_score
                post.spam_reasons = '; '.join(spam_reasons)
                post.is_potentially_spam = True

            logger.info("Setting IP address and saving post")
            post.set_ip_address(ip_address)
            post.ip_address = None
            post.save()
            logger.info(f"Post saved successfully - id: {post.id}, title: {post.title}, content: {post.content}, "
                    f"media file: {post.media_file}, display name {post.display_name}")
            
            # Check if this is an HTMX request
            if self.request.headers.get('HX-Request'):
                logger.info("Processing HTMX request")
                try:
                    context = {
                        'post': post,
                        'is_new': True,
                    }
                    response = render(self.request, 'blog/partials/post.html', context=context)
                    response['HX-Trigger'] = json.dumps({
                        'postCreated': True,
                        'showMessage': 'Post created successfully!'
                    })
                    logger.info("HTMX response created successfully")
                    return response
                except Exception as render_error:
                    logger.error(f"Error rendering HTMX response: {render_error}", exc_info=True)
                    return HttpResponse(
                        f"<div class='alert alert-danger'>Error rendering post: {str(render_error)}</div>",
                        status=500
                    )
            
            # Return JSON response for AJAX requests
            if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
                logger.info("Processing AJAX request")
                return JsonResponse({
                    'success': True, 
                    'post': {
                        'id': post.id,
                        'title': post.title,
                        'content': post.content,
                        'date_posted': localtime(post.date_posted).strftime('%b. %d, %Y, %I:%M %p'),
                        'anon_uuid': post.anon_uuid,
                        'parent_post': {'id': post.parent_post.id, 'title': post.parent_post.title} if post.parent_post else None,
                        'city': post.city,
                        'contact': post.contact,
                        'media_file': {
                            'url': post.media_file.url if post.media_file else None,
                        } if post.media_file else None,
                        'display_name': post.display_name,
                        'image': post.image.url if post.image else None,
                        'is_image': post.is_image, 
                        'is_video': post.is_video,
                    }
                })
            
            logger.info("Processing regular form submission")
            return super().form_valid(form)
            
        except Exception as e:
            logger.error(f"Error in form_valid: {e}", exc_info=True)
            error_message = f"Error creating post: {str(e)}"
            
            if self.request.headers.get('HX-Request'):
                return HttpResponse(
                    f"<div class='alert alert-danger'>{error_message}</div>",
                    status=500
                )
            elif self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_message}, status=500)
            
            messages.error(self.request, error_message)
            return super().form_invalid(form)

    def form_invalid(self, form):
        logger.error("PostCreateView.form_invalid called")
        logger.error("Form errors: %s", form.errors)
        logger.error("Form data: %s", form.data)
        logger.error("Form files: %s", form.files)
        
        # Check if this is an HTMX request
        if self.request.headers.get('HX-Request'):
            logger.info("Returning HTMX error response")
            error_details = f"<div class='alert alert-danger'>Error creating post: {form.errors}</div>"
            logger.info(f"HTMX error response: {error_details}")
            return HttpResponse(error_details, status=400)
        elif self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            logger.info("Returning AJAX error response")
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
        logger.info("Returning super().form_invalid")
        return super().form_invalid(form)


class PostReplyView(PostCreateView):
    template_name = 'blog/post_reply.html'
    form_context_name = 'replyForm'
    form = ReplyForm

    def form_valid(self, form):
        parent_post = get_object_or_404(Post, pk=self.kwargs['pk'])
        reply = form.save(commit=False)

        is_spam, spam_message = self.check_spam_fast(
            self.request,
            reply.name,
            reply.content,
            '',
            media_file=reply.media_file  # This is the uploaded file object
        )
        
        if is_spam:
            logger.warning(f"Spam detected: {spam_message}")
            if self.request.headers.get('HX-Request'):
                return HttpResponse(
                    f"<div class='alert alert-danger'>{spam_message}</div>",
                    status=400
                )
            if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False, 
                    'error': spam_message
                }, status=400)
            messages.error(self.request, spam_message)
            return self.form_invalid(form)


        reply.author = self.request.user
        reply.parent_post = parent_post
        reply.save()
        messages.success(self.request, "Reply successfully posted")
        return redirect('post-detail', pk=parent_post.pk)

    def get_context_data(self, **kwargs):
        logger.info(f"Replying to post {self.kwargs['pk']}")
        context = super().get_context_data(**kwargs)
        context['parent_post'] = get_object_or_404(Post, pk=self.kwargs['pk'])
        logger.info(f"")
        return context

    def post(self, request, *args, **kwargs):
        logger.info("Request POST data: %s", request.POST)  # Log POST data
        logger.info("Request FILES data: %s", request.FILES)
        return super().post(request, *args, **kwargs)



@method_decorator(cache_page(60 * 15), name='dispatch')
class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/post_detail.html'
    context_object_name = 'post'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        return context


@csrf_exempt
def like_post(request, post_id):
    if request.method == 'POST':
        try:
            post = Post.objects.get(id=post_id)
            post.like_count += 1
            post.save()
            return JsonResponse({'like_count': post.like_count})
        except Post.DoesNotExist:
            return JsonResponse({'error': 'Post not found'}, status=404)



class PostListView(ListView):
    model = Post
    template_name = 'blog/post_list.html'  # Specify your template name
    context_object_name = 'posts'  # Name of the context variable to use in the template
    ordering = ['date_posted']  # Order posts by date posted in descending order



def load_more_posts(request):
    """View specifically for handling HTMX load-more requests"""
    page = int(request.GET.get('page', 1))
    logger.info(f"Loading more posts for page {page}")

    # Get posts from cache or database using context processor functions
    posts_data = get_cached_posts()
    posts = posts_data['posts']  # We only need regular posts, not pinned ones
    all_comments = Comment.objects.all().order_by('-created_on')
    
    # Combine posts and comments into a single feed
    combined_items = sorted(
        chain(posts, all_comments),
        key=lambda x: x.date_posted if hasattr(x, 'date_posted') else x.created_on,
        reverse=True
    )
    
    # Create paginator
    paginator = Paginator(combined_items, 20)
    
    try:
        posts_page = paginator.page(page)
    except PageNotAnInteger:
        page = 1
        posts_page = paginator.page(page)
    except EmptyPage:
        page = paginator.num_pages
        posts_page = paginator.page(page)
    
    # Add comment counts for posts
    for item in posts_page:
        if item.get_item_type() == 'Post':
            comments = Comment.objects.filter(post=item).order_by('-created_on')
            item.comments_total = comments.count()
            item.recent_comments = comments
    
    
    context = {
        'posts': posts_page,
    }
    
    return render(request, 'blog/partials/load_more_posts.html', context)


def reading_flyer(request):
    return render(request, 'blog/flyer.html')

def generate_pdf(request):
    # Render HTML template
    html_string = render_to_string('blog/pdf_template.html')

    # Convert the HTML to a PDF
    html = HTML(string=html_string)
    pdf = html.write_pdf()

    # Create a response object and set the appropriate headers
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'inline filename="spite_book.pdf"'

    return response


def preview_pdf_template(request):

    # Render the posts into an HTML template
    return render(request, 'blog/pdf_template.html')

def search_results(request):
    query = request.GET.get('query', '')
    query = query.strip()
    logger.info(f"Searching for: {query}")
    
    if query:
        count = 0 
        # Search in posts with optimized queries
        post_results = Post.objects.filter(
            Q(title__icontains=query) |
            Q(content__icontains=query) |
            Q(display_name__icontains=query)
        ).prefetch_related(
            Prefetch(
                'comments',
                queryset=Comment.objects.order_by('-created_on'),
                to_attr='recent_comments'
            )
        ).distinct()

        count += post_results.count()
        
        # Search in comments with optimized queries
        comment_results = Comment.objects.filter(
            Q(content__icontains=query) |
            Q(name__icontains=query) |
            Q(post__title__icontains=query)
        ).select_related('post').distinct()

        count += comment_results.count()
        
        # Combine and sort results
        combined_items = sorted(
            chain(post_results, comment_results),
            key=lambda x: x.date_posted if hasattr(x, 'date_posted') else x.created_on,
            reverse=True
        )
        
        
        # Paginate combined results
        paginator = Paginator(list(combined_items), 100)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        querylog = SearchQueryLog.objects.create(query=query)
        ip = get_client_ip(request)
        querylog.set_ip_address(ip)
        
        context = {
            'query': query,
            'posts': page_obj,
            'search_query': query,
            'count': count,
            'is_paginated': page_obj.has_other_pages(),
        }
    else:
        context = {
            'query': query, 
            'count': 0,
            'is_paginated': False,
        }
    
    return render(request, 'blog/search_results.html', context)


def store_page(request):

    return render(request, 'blog/products.html')

class IncorrectObjectTypeException(Exception):
    def __init__(self):
        pass

    def __str__(self):
        return "Incorrect object type, must be \'Post\' or \'Comment\'"

from django.views.decorators.http import require_http_methods
@require_http_methods(["POST", "OPTIONS"])
def reply_comment(request, comment_id):
    logger.info(f"reply_comment: Received reply to comment {comment_id}")
    try:
        parent_comment = get_object_or_404(Comment, id=comment_id)
        if not parent_comment:
            return redirect('post-detail', pk=post.id)

        post = parent_comment.post
        logger.info(f"reply_comment: Found parent comment {parent_comment.id} for post {post.id}")

        if request.method == 'POST':
            logger.info(f"reply_comment: POST data: {request.POST}")
            logger.info(f"reply_comment: FILES: {request.FILES}")
            
            form = CommentForm(request.POST, request.FILES)
            if form.is_valid():
                logger.info("reply_comment: Form is valid")
                comment = form.save(commit=False)
                comment.post = post

                if parent_comment:
                    comment.parent_comment = parent_comment
                
                comment.ip_address = get_client_ip(request)
                comment.save()
                logger.info(f"reply_comment: Saved comment with ID {comment.id}")

                # Return json response for ajax requests
                if request.headers.get('HX-Request'):
                    context = {
                        'post': comment,
                    }
                    response = render(request, 'blog/partials/comment.html', context=context)
                    # Add debug headers
                    response['Access-Control-Allow-Origin'] = '*'
                    response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
                    response['Access-Control-Allow-Headers'] = 'X-Requested-With, Content-Type, X-CSRFToken'

                    return response

            elif request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'comment': {
                        'name': comment.name,
                        'content': comment.content,
                        'created_on': localtime(comment.created_on).strftime('%b. %d, %Y, %I:%M %p'),
                        'media_file': {
                            'url': comment.media_file.url if comment.media_file else None,
                        } if comment.media_file else None,
                        'is_image': comment.is_image,
                        'is_video': comment.is_video,
                        'post_id': post.id,
                        'post_title': post.title,
                        'post_content': post.content,
                        'post_media_file': {
                            'url': post.media_file.url if post.media_file else None,
                        } if post.media_file else None,
                        'has_parent_comment': comment.has_parent_comment,
                        'parent_comment_id': comment.parent_comment.id if comment.has_parent_comment else None,
                        'parent_comment_content': comment.parent_comment.content if comment.has_parent_comment else None,
                        'parent_comment_name': comment.parent_comment.name if comment.has_parent_comment else None,
                        'parent_comment_media_file': {
                            'url': comment.parent_comment.media_file.url if comment.parent_comment.media_file else None,
                        } if comment.parent_comment.media_file else None,
                    }
                })

            # Non-AJAX fallback
            return redirect('post-detail', pk=post.id)
    except Exception as e:
        logger.error(f"Error in reply_comment: {e}")
        if request.headers.get('HX-Request'):
            return HttpResponse(
                f"<div class='alert alert-danger'>Error in reply_comment: {e}</div>",
                status=500
            )
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return redirect('post-detail', pk=post.id)

def hx_get_post(request, post_id):
    logger.info(f"hx_get_post: called with post_id: {post_id}")
    try:
        post = get_object_or_404(Post, id=post_id)
        return render(request, 'blog/partials/post.html', {'post': post, 'htmx': True})
    except Exception as e:
        logger.exception(f"hx_get_post: Error in hx_get_post: {str(e)}")
        return HttpResponse(f"Error loading post: {str(e)}", status=500)

def hx_get_comment(request, comment_id=None, comment=None, inline=False):
    """HTMX endpoint to get a single comment"""
    logger.info(f"hx_get_comment: called with comment_id: {comment_id}, inline: {inline}")
    
    try:
        # Get comment with related post data
        if comment_id and not comment:
            comment = get_object_or_404(
                Comment.objects.select_related('post'), 
                id=comment_id
            )
        elif not comment and not comment_id:
            logger.error("hx_get_comment: No comment or comment_id provided")
            return HttpResponse("Comment not found", status=404)

        logger.info(f"hx_get_comment: Rendering comment {comment.id} with inline={inline}")
        
        # Prepare context with all necessary data
        context = {
            'comment': comment,
        }

        template_name = 'blog/partials/inline_comment.html' if inline else 'blog/partials/comment_content.html'
        logger.info(f"hx_get_comment: Using template: {template_name}")
        
        response = render(request, template_name, context)
        logger.info(f"hx_get_comment: Rendered response with status {response.status_code}")
        
        return response

    except Exception as e:
        logger.exception(f"hx_get_comment: Error in hx_get_comment: {str(e)}")
        return HttpResponse(f"Error loading comment: {str(e)}", status=500)

def hx_get_comment_by_id(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    return hx_get_comment(request, comment_id=comment.id, comment=comment, inline=False)

def add_comment(request, post_id, post_type='Post'):
    logger.info(f"add_comment: Received add_comment request for post_id: {post_id}, post_type: {post_type}")
    if post_type == 'Post':
        post = get_object_or_404(Post, id=post_id)
        parent_comment = None
    elif post_type == 'Comment':
        parent_comment = get_object_or_404(Comment, id=post_id) 
        post = parent_comment.post 
    else:
        raise IncorrectObjectTypeException()


    if request.method == 'POST':
        form = CommentForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                comment = form.save(commit=False)
                # every comment has a post
                # if a comment is a child comment its post is the post of its parent 
                comment.post = post

            
                if parent_comment: 
                    comment.parent_comment = parent_comment

                comment.ip_address = get_client_ip(request)

                comment.save()

                if request.headers.get('HX-Request'):
                    target = request.headers.get('HX-Target')
                    if target == f'comments-list-{post.id}':
                        return hx_get_comment(request, comment_id=comment.id, comment=comment, inline=True)
                    elif target == f'post-list':
                        return hx_get_comment(request, comment_id=comment.id, comment=comment, inline=False)


                # Prepare consistent comment data structure
                comment_data = {
                    'id': comment.id,
                    'name': comment.name,
                    'content': comment.content,
                    'created_on': localtime(comment.created_on).strftime('%b. %d, %Y, %I:%M %p'),
                    'post_id': comment.post.id,
                    'post_title': comment.post.title,
                    'media_file': {
                        'url': comment.media_file.url if comment.media_file else None,
                        'is_image': comment.media_file and comment.media_file.name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')),
                        'is_video': comment.media_file and comment.media_file.name.lower().endswith(('.mp4', '.webm'))
                    } if comment.media_file else None
                }

                logger.info(f"Comment data: {comment_data}")

                # Return JSON response for AJAX requests
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'comment': comment_data,
                    })

                # Non-AJAX fallback
                return redirect('post-detail', pk=post.id)
            
            except Exception as e:
                logger.error(f"Error in add_comment: {e}")
                return JsonResponse({'success': False, 'error': str(e)}, status=500)
        return JsonResponse({'success': False}, status=400)
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

def custom_csrf_failure(request, reason=""):
    logger.error(f"CSRF failure occurred. Reason: {reason}. Path: {request.path}")

    # Clear the cache
    cache.clear()
    logger.info("Cache cleared.")

    # Redirect to the homepage
    return redirect('home')


def get_csrf_token(request):
    return JsonResponse({'csrfToken': get_token(request)})


def offline_view(request):
    return render(request, 'blog/offline.html')


def get_comment_form(request, post_id):
    """API endpoint to serve a Crispy-rendered CommentForm for a specific post."""
    post = Post.objects.filter(id=post_id).exists()
    logger.info(f"Post exists: {post}")
    if not post:
        return JsonResponse({'error': 'Post not found'}, status=404)

    form = CommentForm()
    form_html = as_crispy_form(form)

    return JsonResponse({
        'form': form_html,
        'action_url': f'/add-comment/{post_id}/',
    })

def get_comment_reply_form_html(request, comment_id):
    """API endpoint to serve a Crispy-rendered CommentForm for a specific post."""
    try:
        # Explicitly get the comment with its related post
        comment = Comment.objects.select_related('post').get(id=comment_id)


        if not comment:
            return JsonResponse({'error': 'Comment not found'}, status=404)
        
        form = CommentForm()
        context = {
            'form': form,
            'comment_id': comment_id,
            'post_id': comment.post.id,
            'parent_comment': comment,
            'post_type': 'Comment',
        }

        form_html = render_to_string('blog/partials/comment_form.html',
                                        context=context,
                                        request=request  # Pass the request to include CSRF token
                                    )
        action_url = reverse("reply-comment", args=[comment.id])            
        logger.info(f"Debug: Generated action_url = {action_url}")
        return JsonResponse({
            'success': True,
            'form': form_html,
            'action_url': action_url, 
        })
    except Exception as e:
        logger.error(f"Error in get_comment_reply_form_html: {e}")
        return JsonResponse({'error': str(e)}, status=500)


def hx_get_comment_reply_form_html(request, comment_id):
    try:
        comment = get_object_or_404(Comment, id=comment_id)
        comment_form = CommentForm()
        
        context = {
            'comment_form': comment_form,
            'comment_id': comment_id,
            'post_id': comment.post.id,
            'post_type': 'Comment'
        }
        
        html = render_to_string('blog/partials/comment_form.html', context, request=request)
        
        # For HTMX requests
        if request.headers.get('HX-Request'):
            return HttpResponse(html)
        
        # For AJAX requests
        return JsonResponse({
            'form': html,
            'action_url': f'/add-comment/comment/{comment_id}/'
        })
    except Exception as e:
        logger.exception(f"Error in hx_get_comment_reply_form_html: {e}")
        if request.headers.get('HX-Request'):
            return HttpResponse(f"Error: {str(e)}", status=500)
        return JsonResponse({'error': str(e)}, status=500)



def get_comment_form_html(request, post_id):
    """API endpoint to serve a Crispy-rendered CommentForm for a specific post."""
    try:
        # Debugging post_id
        logger.info(f"Received post_id: {post_id}")
        post = Post.objects.filter(id=post_id).exists()

        if not post:
            return JsonResponse({'error': 'Post not found'}, status=404)

        form = CommentForm()
        logger.info(f"Debug: Generated form = {form}")
        form_html = render_to_string('blog/partials/comment_form.html',
                                        {'comment_form': form,
                                        'post_id' : post_id,},
                                        request=request  # Pass the request to include CSRF token
                                    )

        action_url = reverse('add-comment', args=[post_id])
        logger.info(f"Debug: Generated action_url = {action_url}")  # Debugging action_url
        return JsonResponse({
            'form': form_html,
            'action_url': action_url, 
        })
    except Exception as e:
        # Log the exception for debugging
        logger.error(f"Error in get_comment_form_html: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class SaveListView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            input_text = data.get('input', '')

            if not input_text:
                return JsonResponse({'success': False, 'error': 'Input cannot be empty.'}, status=400)

            # Save to the database
            new_list = List.objects.create(input=input_text)
            ip = get_client_ip(request)
            new_list.set_ip_address(ip)
            return JsonResponse({'success': True, 'id': new_list.id})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

def get_word_cloud(request):
    entries = List.objects.values_list('input', flat=True)  # Get a list of inputs
    return JsonResponse({'entries': list(entries)})

from functools import wraps

def simple_password_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        password = "bananapizza"
        
        # Check if already authenticated for this session
        if request.session.get('password_verified'):
            return view_func(request, *args, **kwargs)
        
        # Check if password was submitted
        if request.method == 'POST':
            if request.POST.get('password') == password:
                request.session['password_verified'] = True
                return redirect(request.path)
        
        # Show password form
        return render(request, 'blog/forms/password_form.html')
    
    return _wrapped_view

@simple_password_required
def download_posts_as_html_stream(request):
    # Preload comments using Prefetch
    posts = Post.objects.order_by('-date_posted').prefetch_related(
        Prefetch(
            'comments',
            queryset=Comment.objects.order_by('-created_on'),
            to_attr='recent_comments'
        )
    ).iterator()

    def generate_html_content():
        yield """
        <html>
            <head>
                <title>Spite Archive</title>
                <meta charset="UTF-8">
            </head>
            <style>
                body {
                    font-size: 16px; /* Base font size */
                    line-height: 1.5; /* Improve readability */
                    margin: 20px; /* Add some padding */
                }

                h1 {
                    font-size: 24px; /* Larger font size for titles */
                    margin-bottom: 10px;
                }

                h2 {
                    font-size: 20px; /* Adjust subtitle size */
                    margin-bottom: 8px;
                }

                p {
                    font-size: 14px; /* Adjust paragraph size */
                    margin-bottom: 12px;
                }

                small {
                    font-size: 12px; /* Smaller text for metadata */
                }

                img, video {
                    max-width: 100%; /* Ensure media scales properly */
                    display: block;
                    margin: 10px 0;
                }

                @media print {
                    body {
                        -webkit-print-color-adjust: exact; /* Ensure proper color rendering */
                        width: 100%;
                    }

                    @page {
                        size: A4; /* Standard A4 size */
                        margin: 10mm 15mm; /* Top/bottom, left/right margins */
                    }

                    html, body {
                        zoom: 1.2; /* Increase the size of the entire page */
                    }
                    body {
                        font-size: 18px; /* Larger base font for print */
                    }

                    h1 {
                        font-size: 28px; /* Emphasize headings in print */
                    }

                    h2 {
                        font-size: 22px;
                    }

                    p {
                        font-size: 16px;
                    }

                    small {
                        font-size: 14px;
                    }

                    hr {
                        border: 1px solid #ccc;
                        margin: 20px 0;
                    }

                    /* Remove unnecessary elements like links for print */
                    a {
                        text-decoration: none;
                        color: black;
                    }

                    img, video {
                        max-width: 100%; /* Ensure images do not exceed the page width */
                        height: auto;    /* Maintain aspect ratio */
                        page-break-inside: avoid; /* Prevent breaking images across pages */
                    }
                    
                    /* Optional: Add margins around images */
                    img {
                        margin: 10px 0;
                    }
                }
                </style>
            <body>
        """
        yield "<h1 style=\"font-family: cursive;\">Spite Magazine</h1>"

        for post in posts:
            # Yield post content
            yield f"<h1>{escape(post.title)}</h1>"
            author = escape(post.author) if post.author else (escape(post.display_name) if post.display_name else 'Anonymous')
            yield f"<em>by {author}</em>\n"
            yield f"<p>{escape(post.content)}</p>"

            # Handle media files lazily
            media_content = ""
            try:
                if post.media_file and post.is_image:
                    if default_storage.exists(post.media_file.name):
                        media_content = f'<img src="{post.media_file.url}" alt="{post.title}" style="width: 500px; margin-bottom: 20px;" loading="lazy"><br>'

                elif post.image and post.is_image:
                    if default_storage.exists(post.image.name):
                        media_content = f'<img src="{post.image.url}" alt="{post.title}" style="width: 500px; margin-bottom: 20px;" loading="lazy"><br>'
                elif post.media_file and post.is_video:
                    # Check if media file exists before generating the URL
                    if default_storage.exists(post.media_file.name):
                        media_content = f"""
                        <video controls style="width: 500px; margin-bottom: 20px;">
                            <source src="{post.media_file.url}" type="video/mp4" loading="lazy">
                            Your browser does not support the video tag.
                        </video><br>
                        """
            except Exception as e:
                media_content = f"<p style='color: red;'>Error loading media: {escape(str(e))}</p>"

            yield media_content

            # Post metadata
            yield f'<small><a href="/post/{post.id}/">Post #{post.id}</a> -- {post.date_posted}</small>'

            # Yield preloaded comments
            comments = getattr(post, 'recent_comments', [])
            if comments:
                yield "<h2>Comments</h2>"
                for comment in comments:
                    commenter = escape(comment.name) if comment.name else 'Anonymous'
                    yield f"<p><strong>{commenter}</strong>: {escape(comment.content)}</p>"

            yield "<hr>"

        yield "</body></html>"

    return StreamingHttpResponse(generate_html_content(), content_type="text/html")


def get_media_features(request):
    features_path = os.path.join(settings.MEDIA_ROOT, 'features', 'sorted_media_features.json')
    
    try:
        logger.info(f"Attempting to read features from: {features_path}")
        with open(features_path, 'r') as f:
            features_data = json.load(f)
        logger.info(f"Successfully loaded {len(features_data)} features")
        return JsonResponse({'media_features': features_data})
    except FileNotFoundError:
        logger.warning(f"Features file not found at {features_path}")
        return JsonResponse({'error': 'Features not processed yet'}, status=404)
    except Exception as e:
        logger.error(f"Error loading media features: {str(e)}", exc_info=True)
        return JsonResponse({'error': f'Error loading media features: {str(e)}'}, status=500)


def media_flow(request):
    return render(request, 'blog/media_flow.html')


def media_flow_standalone(request):
    return render(request, 'blog/partials/media_flow_standalone.html')


@contextmanager
def db_connection():
    """Context manager for database connections"""
    try:
        yield
    finally:
        connection.close()

def loading_screen(request):
    """Loading screen view with proper connection management"""
    logger.info("Loading screen view called")
    target_url = request.GET.get('to', '/')
    
    
    retry_count = request.session.get('loading_retry_count', 0)
    return render(request, 'blog/loading.html', {
        'target_url': target_url,
        'retry_count': retry_count
    })

javascript_logger = logging.getLogger('javascript')

@csrf_exempt
@require_POST
def log_javascript(request):
    javascript_logger.info(f"Received JS log request")
    
    try:
        message = request.POST.get('message', '')
        level = request.POST.get('level', 'info')
        
        if level == 'error':
            javascript_logger.error(f"JS Log: {message}")
        elif level == 'warning':
            javascript_logger.warning(f"JS Log: {message}")
        else:
            javascript_logger.info(f"JS Log: {message}")
            
        return JsonResponse({'status': 'logged'})
    except Exception as e:
        javascript_logger.error(f"Error in log_javascript view: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

@simple_password_required
def resume(request):
    return render(request, 'blog/resume.html')

def remove_user(request):
    """Remove user from online users when they disconnect"""
    # Create a unique ID without using raw IP and user agent
    ip = get_client_ip(request)
    storage = SecureIPStorage()
    encrypted_ip = storage.encrypt_ip(ip)
    
    # Hash the user agent instead of using it directly
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    user_agent_hash = hashlib.md5(user_agent.encode()).hexdigest()[:8]
    
    client_id = f"{encrypted_ip[:16]}_{user_agent_hash}"
    online_users = cache.get('online_users', {})
    
    if client_id in online_users:
        del online_users[client_id]
        cache.set('online_users', online_users, 60)
    
    return HttpResponse(str(len(online_users)))

def update_online_status(request):
    """Update user's online status and return total online count"""
    current_time = int(time.time())
    client_id = request.META.get('REMOTE_ADDR', '') + request.META.get('HTTP_USER_AGENT', '')
    
    # Get current online users dict from cache
    online_users = cache.get('online_users', {})
    
    # Check if this is an active chat ping
    is_active_chat = 'HX-Trigger' in request.headers and request.headers['HX-Trigger'] == 'activeChatPing'
    
    # Update this user's timestamp
    online_users[client_id] = current_time
    
    # Remove users who haven't checked in for 30 seconds (or 5 seconds for active chat users)
    cutoff_time = current_time - (5 if is_active_chat else 30)
    online_users = {k: v for k, v in online_users.items() if v > cutoff_time}
    
    # Save back to cache with longer TTL for active chat users
    cache_ttl = 300 if is_active_chat else 60  # 5 minutes for active chat, 1 minute otherwise
    cache.set('online_users', online_users, cache_ttl)
    
    # Return just the number for HTMX to update the span content
    return HttpResponse(str(len(online_users)))

def hx_get_parent_post(request, post_id, inline=False):
    post = get_object_or_404(Post, id=post_id)
    logger.info(f"HX GET Parent Post: {post}")
    response = render(request, 'blog/partials/post.html', 
                    {'post': post, 'nested': True})
    logger.info(f"HX GET Parent Post Response: {response}")
    return response

def hx_scroll_to_post_form(request):
    """HTMX endpoint to scroll to the post form"""
    response = HttpResponse()
    response['HX-Trigger'] = json.dumps({
        'scrollToPostForm': True
    })
    return response


@require_GET
def toggle_version(request):
    # Get current version from session or default to 2.0
    current_version = request.session.get('site_version', '2.0')
    
    # Toggle version
    new_version = '1.0' if current_version == '2.0' else '2.0'
    
    # Save to session
    request.session['site_version'] = new_version
    
    # Set response with new version
    response = HttpResponse(new_version)
    
    # Add header to trigger JS event
    response['HX-Trigger'] = json.dumps({
        'versionChanged': {
            'version': new_version
        }
    })
    
    return response

def hx_get_post_comment_section(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    comment_form = CommentForm()
    context = {'post': post, 'post_id' : post_id, 'comment_form' : comment_form}
    return render(request, 'blog/partials/comment_section.html', context)


def spite_tv(request):
    return render(request, 'blog/spite_tv.html')

def hx_get_comment_chain(request, comment_id):
    # htmx endpoint to fetch a comments chain of parent comments
    try:
        comment = get_object_or_404(Comment, id=comment_id)
        comment_chain = []
        current = comment 
        while current.parent_comment:
            current = current.parent_comment
            comment_chain.append(current)
        
        context = {
            'comment_chain': comment_chain,
            'original_comment_id': comment_id,
        }

        return render(request, 'blog/partials/comment_chain.html', context=context)

    except Exception as e:
        logger.exception(f'Error in hx_get_comment_chain {str(e)}')
        return HttpResponse(f"Error loading comment chain: {str(e)}", status=500)


def spite_counter(request):
    return render(request, 'blog/spite_counter.html', {'SPITE_COUNT': Post.objects.count() + Comment.objects.count(), 'DATE': datetime.now().strftime('%B %d, %Y')})

def htmx_health_check(request):
    """Simple health check endpoint for HTMX debugging"""
    return HttpResponse("HTMX endpoint is working", content_type="text/plain")

def htmx_test_post(request):
    """Test endpoint to simulate a simple post creation for debugging"""
    if request.method == 'POST':
        try:
            # Log the request details
            logger.info(f"HTMX test post received - headers: {dict(request.headers)}")
            logger.info(f"POST data: {request.POST}")
            logger.info(f"FILES data: {request.FILES}")
            
            # Check if this is an HTMX request
            if request.headers.get('HX-Request'):
                logger.info("This is an HTMX request")
                return HttpResponse(
                    "<div class='alert alert-success'>HTMX test post successful! HTMX is working.</div>",
                    content_type="text/html"
                )
            else:
                logger.info("This is NOT an HTMX request")
                return HttpResponse(
                    "<div class='alert alert-warning'>Not an HTMX request</div>",
                    content_type="text/html"
                )
        except Exception as e:
            logger.error(f"Error in htmx_test_post: {e}", exc_info=True)
            return HttpResponse(
                f"<div class='alert alert-danger'>Test post failed: {str(e)}</div>",
                content_type="text/html",
                status=500
            )
    
    return HttpResponse(
        "<div class='alert alert-info'>Send a POST request to test HTMX</div>",
        content_type="text/html"
    )

def htmx_debug_view(request):
    """Debug view for testing HTMX functionality"""
    return render(request, 'blog/htmx_debug.html')


def spam_monitor_view(request):
    """Admin view to monitor spam detection"""
    try:
        # Get spam statistics
        temp_view = PostCreateView()
        spam_stats = temp_view.get_spam_stats()
        
        # Get recent posts with spam scores
        from blog.models import Post
        recent_spam_posts = Post.objects.filter(
            spam_score__gt=0
        ).order_by('-date_posted')[:20]
        
        context = {
            'spam_stats': spam_stats,
            'recent_spam_posts': recent_spam_posts,
        }
        
        return render(request, 'blog/spam_monitor.html', context)
        
    except Exception as e:
        logger.error(f"Error in spam monitor view: {e}")
        return HttpResponse(f"Error: {str(e)}", status=500)


