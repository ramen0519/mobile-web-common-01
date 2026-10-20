from django.urls import path, include
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
router.register('Post', views.BlogImages)

urlpatterns = [
    path('', views.post_list, name='post_list'),
    path('post/<int:pk>/', views.post_detail, name='post_detail'),
    path('post/new/', views.post_new, name='post_new'),
    path('post/<int:pk>/edit/', views.post_edit, name='post_edit'),
    path('post/<int:pk>/like/', views.post_like, name='post_like'),
    path('post/<int:pk>/comment/', views.comment_new, name='comment_new'),
    path('comment/<int:pk>/delete/', views.comment_delete, name='comment_delete'),
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/<int:pk>/', views.notification_read, name='notification_read'),
    path('notifications/read_all/', views.notification_read_all, name='notification_read_all'),
    path('notifications/count/', views.notification_count, name='notification_count'),
    path('draft/save/', views.draft_save, name='draft_save'),
    path('draft/delete/', views.draft_delete, name='draft_delete'),
    path('chat/', views.chat, name='chat'),
    path('accounts/signup/', views.signup, name='signup'),
    path('accounts/signup/send_code/', views.send_code, name='send_code'),
    path('accounts/signup/verify_code/', views.verify_code, name='verify_code'),
    path('accounts/kakao/login/', views.kakao_login, name='kakao_login'),
    path('accounts/kakao/callback/', views.kakao_callback, name='kakao_callback'),
    path('js_test/', views.js_test, name='js_test'),
    path('api_root/', include(router.urls)),
]