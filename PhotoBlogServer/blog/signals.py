from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Like, Comment, Notification

@receiver(post_save, sender=Like)
def like_saved(sender, instance, created, **kwargs):
    # 남의 글에 좋아요를 누르면 글쓴이에게 알림
    if created and instance.user != instance.post.author:
        Notification.objects.create(user=instance.post.author, sender=instance.user, post=instance.post, like=instance)
    cache.delete('ranking')

@receiver(post_save, sender=Comment)
def comment_saved(sender, instance, created, **kwargs):
    # 남의 글에 댓글을 달면 글쓴이에게 알림
    if created and instance.author != instance.post.author:
        Notification.objects.create(user=instance.post.author, sender=instance.author, post=instance.post, comment=instance)
    cache.delete('ranking')

@receiver(post_delete, sender=Like)
@receiver(post_delete, sender=Comment)
def reaction_deleted(sender, instance, **kwargs):
    # 좋아요 취소, 댓글 삭제도 인기 글 순위에 바로 반영
    cache.delete('ranking')
