from django.contrib import admin
from .models import Artwork, Bio, Category

admin.site.register(Artwork)
admin.site.register(Bio)
admin.site.register(Category)