from django.shortcuts import redirect, render
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView, DetailView, ListView
from .models import Post
from django.contrib import messages
from .forms import PostForm
import functools
from datetime import datetime 
import subprocess
# Create your views here.


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


@log_ip
def home(request):
    return render(request, 'blog/home.html')


class PostCreateView(CreateView):
    model = Post
    fields = ['title', 'city', 'description', 'contact', 'image']

    template_name = 'blog/post_form.html'
    
    def get(self, request, *args, **kwargs):
        log_ip1(request, 'get-post')
        context = {
            'postForm': PostForm(),
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):

        log_ip1(request, 'post-post')
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            form.author = request.user
            messages.success(request, "successfully posted")

            
            venv_activate = '/home/sargent/spite/.spite/bin/activate'

            try: 
                subprocess.run(f'source {venv_activate} && python backup_database.py', shell=True, check=True, executable='/bin/bash')
                print('Post uploaded, migrations run, and backup created successfully.')

            except subprocess.CalledProcessError as e:
                print('Post uploaded and migrations run, but backup failed: {str(e)}')   

            return redirect('home')

        return render(request, self.template_name, {'postForm': form})


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
    ordering = ['-date_posted']  # Order posts by date posted in descending order
