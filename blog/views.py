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
from django.views.decorators.cache import cache_page
import logging
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
import os
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.generic import CreateView, DetailView, ListView
from django.views import View
from blog.models import Post, Comment, SearchQueryLog, PageView, List
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
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from difflib import SequenceMatcher
import hashlib
import lz4
import pickle
import time
import requests
from django.db import connection

logger = logging.getLogger('spite')

def write_ip(ip, *args, **kwargs):
    with open('iplog', 'a+') as log:
            entry = datetime.now().strftime("%Y-%m-%d %H:%M:%S") + f' -- {ip}'
            log.write(entry)
            if args or kwargs:
                log.write(f'--- {" ".join([*args, *kwargs.values()])}')
            log.write('\n')


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


def log_ip1(request, *args, **kwargs):
    ip = request.META.get('HTTP_X_FORWARDED_FOR')
    if ip:
        ip = ip.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')

    write_ip(ip, *args, **kwargs)
    
def log_ip(view_func):
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        ip = request.META.get('HTTP_X_FORWARDED_FOR')
        if ip:
            ip = ip.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')

        write_ip(ip, *args, **kwargs)

        return view_func(request, *args, **kwargs)

    return wrapper


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
    logger.info("IP Address for debug-toolbar: " + get_client_ip(request))
    
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
        client_ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
        
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
        
        # Create content hash including name
        content_to_check = f"{title.lower().strip() if title else ''} {content.lower().strip() if content else ''} {author_name.lower().strip() if author_name else ''}"
        content_hash = hashlib.md5(content_to_check.encode()).hexdigest()
        
        # Check for duplicate or similar content
        for recent_hash in recent_posts:
            if content_hash == recent_hash:
                return True, "This looks like a duplicate post"
        
        # Check content similarity with recent posts
        for recent_post in Post.objects.filter(
            date_posted__gte=localtime() - timedelta(minutes=5)
        ).order_by('-date_posted')[:10]:
            similarity = SequenceMatcher(
                None,
                content_to_check,
                f"{recent_post.title.lower().strip() if recent_post.title else ''} \
                {recent_post.content.lower().strip() if recent_post.content else ''} \
                {recent_post.display_name.lower().strip() if recent_post.display_name else ''}"
            ).ratio()
            
            if similarity > 0.8:  # 80% similarity threshold
                return True, "This content is too similar to a recent post"
        
        # Store this content hash
        recent_posts.append(content_hash)
        if len(recent_posts) > 10:  # Keep last 10 posts
            recent_posts.pop(0)
        cache.set(recent_posts_key, recent_posts, 300)  # Store for 5 minutes
        
        return False, ""
 
    def post(self, request, *args, **kwargs):
        logger.info("Request POST data: %s", request.POST)
        logger.info("Request FILES data: %s", request.FILES)
        
        csrf_token_post = request.POST.get('csrfmiddlewaretoken', 'Not found')
        csrf_token_cookie = request.COOKIES.get('csrftoken', 'Not found')
        logger.info(f"CSRF token in POST data: {csrf_token_post}")
        logger.info(f"CSRF token in cookie: {csrf_token_cookie}")

        # Check for spam before processing the form
        is_spam, spam_message = self.check_spam(
            request, 
            request.POST.get('title', ''),
            request.POST.get('content', ''), 
            request.POST.get('display_name', '')
        )
        
        if is_spam:
            logger.warning(f"Spam detected: {spam_message}")
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False, 
                    'error': spam_message
                }, status=400)
            # For non-AJAX requests, add error to messages
            messages.error(request, spam_message)
            return self.form_invalid(self.get_form())

        return super().post(request, *args, **kwargs)
    
    def form_valid(self, form):
        logger.info("Form submitted successfully via %s", self.request.headers.get('x-requested-with'))
        logger.info(f"Form data: {form.cleaned_data}")
        
        # Save the form and get the post instance
        post = form.save(commit=False)
        
        # Add IP address to the post
        post.ip_address = self.request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or \
                         self.request.META.get('REMOTE_ADDR')
        
        post.save()
        logger.info(f"Post id: {post.id}, title: {post.title}, content: {post.content}, "
                   f"media file: {post.media_file}, display name {post.display_name}")
        
        post = get_object_or_404(Post, pk=post.id)
        
        # Return JSON response for AJAX requests
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
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
                    'is_image': post.is_image(), 
                    'is_video': post.is_video(),
                }
            })
        return super().form_valid(form)

    def form_invalid(self, form):
        logger.error("Form errors: %s", form.errors)
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
        return super().form_invalid(form)


class PostReplyView(PostCreateView):
    template_name = 'blog/post_reply.html'
    form_context_name = 'replyForm'
    form = ReplyForm

    def form_valid(self, form):
        parent_post = get_object_or_404(Post, pk=self.kwargs['pk'])
        reply = form.save(commit=False)
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
# @log_ip
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
    page = request.GET.get('page', 1)
    
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
        posts_page = paginator.page(1)
    except EmptyPage:
        posts_page = paginator.page(paginator.num_pages)
    
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
    logger.info(f"Searching for: {query}")
    
    if query:
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
        
        # Search in comments with optimized queries
        comment_results = Comment.objects.filter(
            Q(content__icontains=query) |
            Q(name__icontains=query) |
            Q(post__title__icontains=query)
        ).select_related('post').distinct()
        
        # Combine and sort results
        combined_items = sorted(
            chain(post_results, comment_results),
            key=lambda x: x.date_posted if hasattr(x, 'date_posted') else x.created_on,
            reverse=True
        )
        
        # Paginate combined results
        paginator = Paginator(list(combined_items), 10)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        
        context = {
            'query': query,
            'posts': page_obj,  # This matches your feed.html template's expectation
            'search_query': query,  # Keep the original query for the template
        }

    else:
        context = {'query': query}
    
    return render(request, 'blog/search_results.html', context)


def store_page(request):

    return render(request, 'blog/shop.html')

class IncorrectObjectTypeException(Exception):
    def __init__(self):
        pass

    def __str__(self):
        return "Incorrect object type, must be \'Post\' or \'Comment\'"


def reply_comment(request, comment_id):
    parent_comment = get_object_or_404(Comment, id=comment_id)
    post = parent_comment.post

    if request.method == 'POST':
        form = CommentForm(request.POST, request.FILES)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post

            if parent_comment:
                comment.parent_comment = parent_comment
            
            comment.ip_address = get_client_ip(request)
            comment.save()

            # Return json response for ajax requests
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'comment': {
                        'name': comment.name,
                        'content': comment.content,
                        'created_on': localtime(comment.created_on).strftime('%b. %d, %Y, %I:%M %p'),
                        'media_file': {
                            'url': comment.media_file.url if comment.media_file else None,
                        } if comment.media_file else None,
                        'is_image': comment.is_image(),
                        'is_video': comment.is_video(),
                        'post_id': post.id,
                        'post_title': post.title,
                        'post_content': post.content,
                        'post_media_file': {
                            'url': post.media_file.url if post.media_file else None,
                        } if post.media_file else None,
                        'has_parent_comment': comment.has_parent_comment(),
                        'parent_comment_id': comment.parent_comment.id if comment.has_parent_comment() else None,
                        'parent_comment_content': comment.parent_comment.content if comment.has_parent_comment() else None,
                        'parent_comment_name': comment.parent_comment.name if comment.has_parent_comment() else None,
                        'parent_comment_media_file': {
                            'url': comment.parent_comment.media_file.url if comment.parent_comment.media_file else None,
                        } if comment.parent_comment.media_file else None,
                    }
                })

            # Non-AJAX fallback
            return redirect('post-detail', pk=post.id)

    return JsonResponse({'success': False}, status=400)


def add_comment(request, post_id, post_type='Post'):
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
            'parent_comment': comment
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
            new_list = List.objects.create(input=input_text,
                                        ip_address=get_client_ip(request),)
            return JsonResponse({'success': True, 'id': new_list.id})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

def get_word_cloud(request):
    entries = List.objects.values_list('input', flat=True)  # Get a list of inputs
    return JsonResponse({'entries': list(entries)})


def download_posts_as_html_stream(request):
    # Preload comments using Prefetch
    posts = Post.objects.prefetch_related(
        Prefetch(
            'comments',
            queryset=Comment.objects.order_by('-created_on'),
            to_attr='recent_comments'  # Preloaded comments are stored here
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


def loading_screen(request):
    """Loading screen view that periodically checks server status"""
    logger.info("Loading screen view called")
    target_url = request.GET.get('to', '/')
    
    try:
        # Try to fetch the target URL with a timeout
        response = requests.get(
            request.build_absolute_uri(target_url),
            timeout=5,
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        if response.status_code == 200:
            logger.info("Server check successful, redirecting to target")
            redirect_response = redirect(target_url)
            # Set an explicit value and max_age
            redirect_response.set_cookie(
                'loading_complete', 
                'true', 
                path='/',
                max_age=3600,  # 1 hour
                httponly=True
            )
            # Reset retry count on success
            request.session['loading_retry_count'] = 0
            return redirect_response
            
    except (requests.Timeout, requests.RequestException) as e:
        logger.error(f"Request error during server check: {e}")
        
    finally:
        # Clean up database connections
        connection.close()
    
    # Show loading screen with retry count
    retry_count = request.session.get('loading_retry_count', 0)
    return render(request, 'blog/loading.html', {
        'target_url': target_url,
        'retry_count': retry_count,
        'error_message': 'Server is starting up...' if retry_count < 3 else 'Taking longer than usual...'
    })

javascript_logger = logging.getLogger('javascript')

@csrf_exempt
@require_POST
def log_javascript(request):
    javascript_logger.info(f"Received JS log request from {request.META.get('REMOTE_ADDR')}")
    javascript_logger.info(f"Headers: {dict(request.headers)}")
    
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

def resume(request):
    return render(request, 'blog/resume.html')

def remove_user(request):
    """Remove user from online users when they disconnect"""
    client_id = request.META.get('REMOTE_ADDR', '') + request.META.get('HTTP_USER_AGENT', '')
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