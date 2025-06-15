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
    return render(request, 'artworks/contact.html')

def portfolio(request):
    categories = Category.objects.all()
    artworks = Artwork.objects.all().order_by('-created_at')
    featured_artwork = artworks.filter(is_featured=True).first()
    return render(request, 'artworks/portfolio.html', {'artworks': artworks, 'categories': categories, 'featured_artwork': featured_artwork})

def portfolio_by_category(request, slug):
    category = get_object_or_404(Category, slug=slug)
    artworks = category.artworks.all().order_by('-created_at')
    categories = Category.objects.all()
    return render(request, 'artworks/portfolio.html', {
        'artworks': artworks,
        'categories': categories,
        'current_category': category
    })

def artwork_detail(request, slug):
    artwork = get_object_or_404(Artwork, slug=slug)
    return render(request, 'artworks/artwork_detail.html', {'artwork': artwork})

def hx_get_artwork_detail(request, slug):
    artwork = get_object_or_404(Artwork, slug=slug)
    category_slug = request.GET.get('category')

    # Get the artwork list (same logic as portfolio view)
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        artworks = Artwork.objects.filter(category=category).order_by('-created_at')
    else:
        artworks = Artwork.objects.all().order_by('-created_at')

    # Find current artwork position
    artwork_list = list(artworks)
    current_index = artwork_list.index(artwork)

    # Get previous and next artworks
    previous_artwork = artwork_list[current_index - 1] if current_index > 0 else None
    next_artwork = artwork_list[current_index + 1] if current_index < len(artwork_list) - 1 else None
    
    prev_artwork = artwork_list[current_index - 1] if current_index > 0 else None
    next_artwork = artwork_list[current_index + 1] if current_index < len(artwork_list) - 1 else None

    context = {
        'artwork': artwork,
        'prev_artwork': prev_artwork,
        'next_artwork': next_artwork,
        'current_category': category_slug,
    }
    return render(request, 'artworks/artwork_detail_stub.html', context)


def flyer(request):
    return render(request, 'artworks/flyer.html')