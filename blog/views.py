from django.shortcuts import redirect, render, get_object_or_404
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
import logging
from django.core.paginator import Paginator
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView, DetailView, ListView
from .models import Post
from django.contrib import messages
from .forms import PostForm, ReplyForm
import functools
from datetime import datetime 
import subprocess
from weasyprint import HTML
# Create your views here.

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

@log_ip
@cache_page(60 * 15, key_prefix=CACHE_KEY)
def home(request):
    logger.debug("IP Address for debug-toolbar: " + get_client_ip(request))
    return render(request, 'blog/home.html')

@method_decorator(cache_page(60 * 15), name='dispatch')
class PostCreateView(CreateView):
    model = Post
    fields = ['title', 'city', 'description', 'contact', 'image']

    template_name = 'blog/post_form.html'
    form_context_name = 'postForm'
    form = PostForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context[self.form_context_name] = self.form()
        return context

    def get(self, request, *args, **kwargs):
        log_ip1(request, 'get-post')
        context = {
            self.form_context_name : self.form(),
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):

        log_ip1(request, 'post-post')
        form = self.form(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            form.author = request.user
            messages.success(request, "successfully posted")

            return redirect('home')
        return render(request, self.template_name, {self.form_context_name: form})

''' 
venv_activate = '/home/sargent/spite/.spite/bin/activate'

try: 
    subprocess.run(f'source {venv_activate} && python backup_database.py', shell=True, check=True, executable='/bin/bash')
    print('Post uploaded, migrations run, and backup created successfully.')

except subprocess.CalledProcessError as e:
    print('Post uploaded and migrations run, but backup failed: {str(e)}')   
'''

@method_decorator(cache_page(60 * 15), name='dispatch')
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
        context = super().get_context_data(**kwargs)
        context['parent_post'] = get_object_or_404(Post, pk=self.kwargs['pk'])
        return context



@method_decorator(cache_page(60 * 15), name='dispatch')
class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/post_detail.html'
    context_object_name = 'post'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        return context


@csrf_exempt
@log_ip
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
    response['Content-Disposition'] = 'inline; filename="spite_book.pdf"'

    return response


def preview_pdf_template(request):

    # Render the posts into an HTML template
    return render(request, 'blog/pdf_template.html')