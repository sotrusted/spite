from django.contrib import admin
from .models import Post, Comment, SearchQueryLog, ChatMessage, List, BlockedIP

admin.site.register(Post)   
admin.site.register(Comment)
admin.site.register(SearchQueryLog)
admin.site.register(ChatMessage)
admin.site.register(List)
admin.site.register(BlockedIP)

class BlockedIPAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'ip_range', 'reason', 'date_blocked', 'is_permanent', 'expires', 'is_active')
    list_filter = ('is_permanent', 'date_blocked')
    search_fields = ('ip_address', 'ip_range', 'reason')

