from blog.models import Post

def load_posts(request):
    posts = Post.objects.all().order_by('-date_posted')
    return {
        'posts': posts,
        'spite' : len(posts)
    }
