from django.contrib import admin
from .models import Post, Profile, EmailCode, Comment, Like, Notification, PostView, Draft, ChatMessage

admin.site.register(Post)
admin.site.register(Profile)
admin.site.register(Comment)
admin.site.register(Like)
admin.site.register(Draft)
admin.site.register(ChatMessage)

@admin.register(EmailCode)
class EmailCodeAdmin(admin.ModelAdmin):
    list_display = ('email', 'code', 'created_date', 'fail_count', 'is_verified')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'sender', 'post', 'like', 'comment', 'is_read', 'created_date')

@admin.register(PostView)
class PostViewAdmin(admin.ModelAdmin):
    list_display = ('post', 'viewer', 'viewed_date', 'created_date')
