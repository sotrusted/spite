from django.shortcuts import render
from .models import Artwork, Bio, Category
from django.shortcuts import get_object_or_404

def home(request):
    bio = Bio.objects.first()
    return render(request, 'artworks/home.html', {'bio': bio})

def about(request):
    bio = Bio.objects.first()
    return render(request, 'artworks/about.html', {'bio': bio})

def contact(request):
    return render(request, 'contact.html')

def portfolio(request):
    categories = Category.objects.all()
    artworks = Artwork.objects.all().order_by('-created_at')
    return render(request, 'artworks/portfolio.html', {'artworks': artworks, 'categories': categories})

def portfolio_by_category(request, slug):
    category = get_object_or_404(Category, slug=slug)
    artworks = category.artworks.all().order_by('-created_at')
    categories = Category.objects.all()
    return render(request, 'portfolio.html', {
        'artworks': artworks,
        'categories': categories,
        'current_category': category
    })