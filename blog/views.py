from django.shortcuts import redirect, render
from django.views.generic import CreateView, DetailView
from .models import Post
from django.contrib import messages
from .forms import PostForm
# Create your views here.

def home(request):
    context = {
        'posts': Post.objects.all()
    }
    return render(request, 'blog/home.html',context)

class PostCreateView(CreateView):
    model = Post
    fields = ['title', 'city', 'description', 'contact', 'image']

    template_name = 'blog/post_form.html'


    def get(self, request, *args, **kwargs):
        context = {
            'postForm': PostForm(),
        }
        return render(request, self.template_name, context)

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
