from django.contrib import admin
from .models import Post, Comment, SearchQueryLog, List

admin.site.register(Post)   
admin.site.register(Comment)
admin.site.register(SearchQueryLog)
admin.site.register(List)
