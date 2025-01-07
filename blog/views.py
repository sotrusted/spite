from django.shortcuts import redirect, render, get_object_or_404
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
from django.core.paginator import Paginator
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
from datetime import datetime 
from spite.context_processors import get_posts
from django.http import StreamingHttpResponse
from weasyprint import HTML
import cv2
import numpy as np
from django.conf import settings

logger = logging.getLogger('spite')

def write_ip(ip, *args, **kwargs):
    with open('iplog', 'a+') as log:
            entry = datetime.now().strftime("%Y-%m-%d %H:%M:%S") + f' -- {ip}'
            log.write(entry)
            if args or kwargs:
                log.write(f'--- {" ".join([*args, *kwargs.values()])}')
            log.write('\n')


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

@cache_page(60 * 15, key_prefix=CACHE_KEY)
@csrf_protect
def home(request):
    logger.info("IP Address for debug-toolbar: " + get_client_ip(request))
    # Get cached pageview count
    cached_count = cache.get('pageview_temp_count', 0)

    # Get persistent pageview count from the database
    persistent_count = PageView.objects.first().count if PageView.objects.exists() else 0

    # Combine counts
    total_pageviews = cached_count + persistent_count

    return render(request, 'blog/home.html', {'pageview_count': total_pageviews})

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
 
    def post(self, request, *args, **kwargs):
        logger.info("Request POST data: %s", request.POST)  # Log POST data
        logger.info("Request FILES data: %s", request.FILES)
        # Log CSRF-related data
        csrf_token_post = request.POST.get('csrfmiddlewaretoken', 'Not found')
        csrf_token_cookie = request.COOKIES.get('csrftoken', 'Not found')
        logger.info(f"CSRF token in POST data: {csrf_token_post}")
        logger.info(f"CSRF token in cookie: {csrf_token_cookie}")
        return super().post(request, *args, **kwargs)
    
    def form_valid(self, form):
        logger.info("Form submitted successfully via %s", self.request.headers.get('x-requested-with'))
        logger.info(f"Form data: {form.cleaned_data}")
        post = form.save()
        logger.info(f"Post id: {post.id}, title: {post.title}, content: {post.content}, media file: {post.media_file}, display name {post.display_name}")
        post = get_object_or_404(Post, pk=post.id)
        # Return JSON response for AJAX requests
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 
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
                                        'url': post.media_file.url if post.media_file.url else None,
                                    } if post.media_file else None,
                                    'display_name': post.display_name,
                                    'image': post.image.url if post.image else None,
                                    'is_image': post.is_image(), 
                                    'is_video': post.is_video(),
                                }})
        return super().form_valid(form)

    def form_invalid(self, form):
        logger.error("Form errors: %s", form.errors)  # Log the form errors
        # Return JSON response for AJAX requests
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
        return super().form_invalid(form)

''' 
venv_activate = '/home/sargent/spite/.spite/bin/activate'

try: 
    subprocess.run(f'source {venv_activate} && python backup_database.py', shell=True, check=True, executable='/bin/bash')
    print('Post uploaded, migrations run, and backup created successfully.')

except subprocess.CalledProcessError as e:
    print('Post uploaded and migrations run, but backup failed: {str(e)}')   
'''

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
    post_list = Post.objects.all().order_by('-date_posted')
    paginator = Paginator(post_list, 100)

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'posts': page_obj,
        'is_paginated': page_obj.has_other_pages(),
    }
    return render(request, 'blog/post_list_partial.html', context)


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
    query = request.GET.get('query')
    if query:
        logger.info(f'Search query: {query}')
        SearchQueryLog.objects.create(
            query=query,
            user=request.user if request.user.is_authenticated else None,
            ip_address=get_client_ip(request),
            timestamp=now()
        )
        posts = Post.objects.filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        ).order_by('-date_posted')
    else:
        posts = Post.objects.none()
    
    context = {
        'posts': posts,
        'query': query,
    }

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
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post

            if parent_comment:
                comment.parent_comment = parent_comment
            
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
                            'url': comment.media_file.url if comment.media_file.url else None,
                        } if comment.media_file else None,
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
            comment = form.save(commit=False)
            # every comment has a post
            # if a comment is a child comment its post is the post of its parent 
            comment.post = post

        
            if parent_comment: 
                comment.parent_comment = parent_comment

            comment.save()

            # Return JSON response for AJAX requests
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'comment': {
                        'name': comment.name,
                        'content': comment.content,
                        'created_on': localtime(comment.created_on).strftime('%b. %d, %Y, %I:%M %p'),
                    }
                })

            # Non-AJAX fallback
            return redirect('post-detail', pk=post.id)

    return JsonResponse({'success': False}, status=400)

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

def get_comment_reply_form(request, comment_id):
    """API endpoint to serve a Crispy-rendered CommentForm for a specific post."""
    comment = Comment.objects.filter(id=comment_id).exists()

    if not comment:
        return JsonResponse({'error': 'Comment not found'}, status=404)

    form = CommentForm()
    form_html = as_crispy_form(form)

    return JsonResponse({
        'form': form_html,
        'action_url': f'/add-comment/comment/{comment_id}/',
    })



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

        action_url = reverse('add_comment', args=[post_id])
        logger.info(f"Debug: Generated action_url = {action_url}")  # Debugging action_url
        # Append the button
        return JsonResponse({
            'form': form_html,
            'action_url': action_url, 
        })
    except Exception as e:
        # Log the exception for debugging
        logger.info(f"Error in get_comment_form_html: {e}")
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
    features_path = os.path.join(settings.MEDIA_ROOT, 'features', 'media_features.json')
    
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
    logger.info("Loading screen view called")
    logger.info(f"Query parameters: {request.GET}")
    logger.info(f"Current cookies: {request.COOKIES}")
    
    response = render(request, 'blog/loading.html')
    
    # Set the cookie in the response
    response.set_cookie('loading_complete', 'true', path='/')
    logger.info("Set loading_complete cookie in response")
    
    return response