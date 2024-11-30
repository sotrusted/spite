from django.shortcuts import redirect, render, get_object_or_404
from django.views.decorators.cache import never_cache
from django.middleware.csrf import get_token
from django.http import JsonResponse
from django.utils.timezone import localtime, now
from django.urls import reverse_lazy
from django.core.cache import cache
from django.db.models import Q
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
import logging
from django.core.paginator import Paginator
# import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.generic import CreateView, DetailView, ListView
from blog.models import Post, Comment, SearchQueryLog
from django.contrib import messages
from blog.forms import PostForm, ReplyForm, CommentForm
import functools
from datetime import datetime 
# import subprocess
# from weasyprint import HTML

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
    return render(request, 'blog/home.html')

class PostCreateView(CreateView):
    model = Post
    fields = ['title', 'city', 'content', 'contact', 'image', 'media_file']

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
        logger.info(f"Post id: {post.id}, title: {post.title}, content: {post.content}, media file: {post.media_file}")
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

def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
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