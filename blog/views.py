from django.shortcuts import redirect, render
from django.views.generic import CreateView, DetailView
from .models import Post
from django.contrib import messages
from .forms import PostForm
import functools
# Create your views here.

def log_ip_args(view_func):
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        ip = request.META.get('HTTP_X_FORWARDED_FOR')
        if ip:
            ip = ip.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')

        with open('iplog', 'a+') as log:
            log.write(ip)
            log.write(f': {args.join()}')
            log.write('\n')

        return view_func(request, *args, **kwargs)

    return wrapper

@log_ip
def home(request):

    ip = request.META.get('HTTP_X_FORWARDED_FOR')

    if ip:
        ip = ip.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')

    with open('iplog', 'a+') as log:
        log.write(ip)
        
        log.write('\n')

    return render(request, 'blog/home.html')

class PostCreateView(CreateView):
    model = Post
    fields = ['title', 'city', 'description', 'contact', 'image']

    template_name = 'blog/post_form.html'
    
    @log_ip
    def get(self, request, *args, **kwargs):
        context = {
            'postForm': PostForm(),
        }
        
        ip = request.META.get('HTTP_X_FORWARDED_FOR')
        if ip:
           ip = ip.split(',')[0]
        else:
           ip = request.META.get('REMOTE_ADDR')
        

        return render(request, self.template_name, context)
    
    @log_ip_args
    def post(self, request, *args, **kwargs):

        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            form.author = request.user
            messages.success(request, "successfully posted")
            return redirect('home')

        return render(request, self.template_name, {'postForm': form})
            

class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/post_detail.html'
    context_object_name = 'post'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        return context
