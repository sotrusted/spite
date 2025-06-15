from django.contrib import admin
from django.utils.html import format_html
from .models import Artwork, Bio, Category
from adminsortable2.admin import SortableAdminMixin

@admin.register(Artwork)
class ArtworkAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ('thumbnail', 'title', 'category', 'created_at')
    list_per_page = 50
    list_filter = ('category', 'created_at')
    search_fields = ('title', 'category__name')
    exclude = ('slug',)
    ordering = ['-order']  # Default to descending order
    
    def thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 4px;" />', obj.image.url)
        return "No Image"
    thumbnail.short_description = 'Thumbnail'

@admin.register(Bio)
class BioAdmin(admin.ModelAdmin):
    list_display = ('last_updated',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    prepopulated_fields = {'slug': ('name',)}
