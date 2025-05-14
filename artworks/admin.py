from django.contrib import admin
from .models import Artwork, Bio, Category

@admin.register(Artwork)
class ArtworkAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'created_at', 'slug', 'image')
    list_filter = ('category', 'created_at')
    search_fields = ('title', 'category__name')
    exclude = ('slug',)

@admin.register(Bio)
class BioAdmin(admin.ModelAdmin):
    list_display = ('last_updated',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    prepopulated_fields = {'slug': ('name',)}
