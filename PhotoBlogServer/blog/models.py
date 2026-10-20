from django.db import models
from django.utils import timezone

class Post(models.Model):
    author = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    text = models.TextField()
    created_date = models.DateTimeField(default=timezone.now)
    published_date = models.DateTimeField(blank=True, null=True)
    image = models.ImageField(upload_to='images/%Y/%m/%d/', default='images/default_error.png')
    view_count = models.PositiveIntegerField(default=0)  # 조회수 (같은 사람은 하루 한 번)

    def publish(self):
        self.published_date = timezone.now()
        self.save()

    def __str__(self):
        return self.title

class Profile(models.Model):
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE)
    nickname = models.CharField(max_length=20, unique=True)
    kakao_id = models.CharField(max_length=30, unique=True, blank=True, null=True)  # 카카오 회원번호

    def __str__(self):
        return self.nickname

class EmailCode(models.Model):
    # 회원가입 이메일 인증코드
    email = models.EmailField()
    code = models.CharField(max_length=6)
    created_date = models.DateTimeField(default=timezone.now)
    fail_count = models.PositiveIntegerField(default=0)  # 틀린 횟수
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.email

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    text = models.CharField(max_length=300)
    created_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.text

class Like(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    created_date = models.DateTimeField(default=timezone.now)

    class Meta:
        # 한 사람은 한 글에 좋아요 한 번만
        constraints = [models.UniqueConstraint(fields=['post', 'user'], name='unique_like')]

class Notification(models.Model):
    # 내 글에 좋아요, 댓글이 달리면 생기는 알림 (좋아요 취소, 댓글 삭제 시 같이 지워짐)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='notifications')  # 받는 사람
    sender = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='+')
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    like = models.ForeignKey(Like, on_delete=models.CASCADE, blank=True, null=True)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_date = models.DateTimeField(default=timezone.now)

class PostView(models.Model):
    # 조회 기록 (인기 글 순위 계산에 씀)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='post_views')
    viewer = models.CharField(max_length=60)  # 'user:번호' 또는 'session:세션키'
    viewed_date = models.DateField()
    created_date = models.DateTimeField(default=timezone.now)

    class Meta:
        # 같은 사람은 하루에 한 번만 기록
        constraints = [models.UniqueConstraint(fields=['post', 'viewer', 'viewed_date'], name='unique_post_view')]

class Draft(models.Model):
    # 글쓰기 자동 임시 저장 (새 글이면 post가 비어 있음)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, blank=True, null=True)
    title = models.CharField(max_length=200, blank=True)
    text = models.TextField(blank=True)
    updated_date = models.DateTimeField(auto_now=True)

class ChatMessage(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    text = models.CharField(max_length=500)
    created_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.text