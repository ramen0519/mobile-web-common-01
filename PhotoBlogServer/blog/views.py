import secrets
import requests
from datetime import timedelta
from urllib.parse import urlencode
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.db.models import Count, F, Q
from .models import Post, Profile, EmailCode, Comment, Like, Notification, PostView, Draft, ChatMessage
from .forms import PostForm, SignupForm
from .templatetags.blog_tags import nickname
from rest_framework import viewsets
from .serializers import PostSerializer

def post_list(request):
    posts = Post.objects.filter(
        published_date__lte=timezone.now()
    ).order_by('published_date').annotate(
        like_count=Count('likes', distinct=True),
        comment_count=Count('comments', distinct=True),
    )
    return render(request, 'blog/post_list.html', {'posts': posts, 'ranking': get_ranking()})

def get_ranking():
    # 실시간 인기 글: 최근 24시간 반응 점수(조회 1, 좋아요 3, 댓글 5) TOP 5
    # 계산 결과는 30초 동안 캐시에 두고, 좋아요나 댓글이 생기면 바로 지움(signals.py)
    ranking = cache.get('ranking')
    if ranking is None:
        since = timezone.now() - timedelta(hours=24)
        ranking = list(Post.objects.filter(
            published_date__lte=timezone.now()
        ).annotate(
            views_24h=Count('post_views', filter=Q(post_views__created_date__gte=since), distinct=True),
            likes_24h=Count('likes', filter=Q(likes__created_date__gte=since), distinct=True),
            comments_24h=Count('comments', filter=Q(comments__created_date__gte=since), distinct=True),
        ).annotate(
            score=F('views_24h') + F('likes_24h') * 3 + F('comments_24h') * 5
        ).filter(score__gt=0).order_by('-score', '-published_date')[:5])
        cache.set('ranking', ranking, 30)
    return ranking

def count_view(request, post):
    # 같은 사람은 하루에 한 번만 조회수를 올림 (로그인은 계정, 아니면 브라우저 세션으로 구분)
    if request.user.is_authenticated:
        viewer = 'user:%d' % request.user.pk
    else:
        if not request.session.session_key:
            request.session.save()
        viewer = 'session:' + request.session.session_key
    view, created = PostView.objects.get_or_create(post=post, viewer=viewer, viewed_date=timezone.localdate())
    if created:
        # DB에서 바로 1을 더함 (여러 명이 동시에 열어도 숫자가 꼬이지 않음)
        Post.objects.filter(pk=post.pk).update(view_count=F('view_count') + 1)
        post.refresh_from_db(fields=['view_count'])

def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    count_view(request, post)
    comments = post.comments.select_related('author__profile').order_by('created_date')
    liked = request.user.is_authenticated and post.likes.filter(user=request.user).exists()
    return render(request, 'blog/post_detail.html', {'post': post, 'comments': comments, 'liked': liked})

@login_required
def post_new(request):
    if request.method == "POST":
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.published_date = timezone.now()
            post.save()
            # 글을 올렸으니 임시 저장은 지움
            Draft.objects.filter(user=request.user, post=None).delete()
            return redirect('post_detail', pk=post.pk)
    else:
        form = PostForm()
    draft = Draft.objects.filter(user=request.user, post=None).first()
    return render(request, 'blog/post_edit.html', {'form': form, 'draft': draft_data(draft)})

@login_required
def post_edit(request, pk):
    post = get_object_or_404(Post, pk=pk)
    # 누구나 가입할 수 있으므로 글쓴이만 수정 가능
    if post.author != request.user:
        return redirect('post_detail', pk=post.pk)
    if request.method == "POST":
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.published_date = timezone.now()
            post.save()
            Draft.objects.filter(user=request.user, post=post).delete()
            return redirect('post_detail', pk=post.pk)
    else:
        form = PostForm(instance=post)
    draft = Draft.objects.filter(user=request.user, post=post).first()
    return render(request, 'blog/post_edit.html', {'form': form, 'draft': draft_data(draft), 'post_id': post.pk})

def draft_data(draft):
    # 템플릿에서 "불러오기"에 쓸 임시 저장 내용
    if draft is None:
        return None
    return {
        'title': draft.title,
        'text': draft.text,
        'saved': timezone.localtime(draft.updated_date).strftime('%m월 %d일 %H:%M'),
    }

@login_required
@require_POST
def draft_save(request):
    post = None
    if request.POST.get('post'):
        post = get_object_or_404(Post, pk=request.POST['post'])
    draft, created = Draft.objects.update_or_create(
        user=request.user, post=post,
        defaults={'title': request.POST.get('title', '')[:200], 'text': request.POST.get('text', '')},
    )
    return JsonResponse({'ok': True, 'saved': timezone.localtime(draft.updated_date).strftime('%H:%M:%S')})

@login_required
@require_POST
def draft_delete(request):
    Draft.objects.filter(user=request.user, post_id=request.POST.get('post') or None).delete()
    return JsonResponse({'ok': True})

@login_required
@require_POST
def post_like(request, pk):
    post = get_object_or_404(Post, pk=pk)
    like = Like.objects.filter(post=post, user=request.user).first()
    if like:
        like.delete()
        liked = False
    else:
        Like.objects.get_or_create(post=post, user=request.user)
        liked = True
    return JsonResponse({'liked': liked, 'count': post.likes.count()})

@login_required
@require_POST
def comment_new(request, pk):
    post = get_object_or_404(Post, pk=pk)
    text = request.POST.get('text', '').strip()
    if not text:
        return JsonResponse({'ok': False, 'message': '댓글 내용을 입력해 주세요.'})
    comment = Comment.objects.create(post=post, author=request.user, text=text[:300])
    return JsonResponse({
        'ok': True,
        'id': comment.pk,
        'nickname': nickname(request.user),
        'text': comment.text,
        'date': timezone.localtime(comment.created_date).strftime('%Y-%m-%d %H:%M'),
        'count': post.comments.count(),
    })

@login_required
@require_POST
def comment_delete(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    if comment.author != request.user:
        return JsonResponse({'ok': False, 'message': '내 댓글만 지울 수 있습니다.'}, status=403)
    post = comment.post
    comment.delete()
    return JsonResponse({'ok': True, 'count': post.comments.count()})

@login_required
def notification_list(request):
    notifications = request.user.notifications.select_related(
        'sender__profile', 'post', 'comment'
    ).order_by('-created_date')[:50]
    return render(request, 'blog/notification_list.html', {'notifications': notifications})

@login_required
def notification_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save()
    return redirect('post_detail', pk=notification.post_id)

@login_required
@require_POST
def notification_read_all(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect('notification_list')

@login_required
def notification_count(request):
    return JsonResponse({'count': request.user.notifications.filter(is_read=False).count()})

@login_required
def chat(request):
    # 최근 대화 50개를 먼저 보여 주고, 새 메시지는 웹소켓(consumers.py)으로 받음
    chat_messages = ChatMessage.objects.select_related('user__profile').order_by('-created_date')[:50]
    return render(request, 'blog/chat.html', {'chat_messages': reversed(list(chat_messages))})

def signup(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            # 이메일 인증을 마친 주소인지 서버에서 다시 확인
            if request.session.get('verified_email') != form.cleaned_data['email']:
                form.add_error('email', '이메일 인증을 완료해 주세요.')
            else:
                user = form.save()
                Profile.objects.create(user=user, nickname=form.cleaned_data['nickname'])
                del request.session['verified_email']
                login(request, user)
                return redirect('post_list')
    else:
        form = SignupForm()
    verified = form['email'].value() and form['email'].value() == request.session.get('verified_email')
    return render(request, 'registration/signup.html', {'form': form, 'verified': verified})

@require_POST
def send_code(request):
    email = request.POST.get('email', '').strip()
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({'ok': False, 'message': '이메일 형식이 올바르지 않습니다.'})
    if User.objects.filter(email__iexact=email).exists():
        return JsonResponse({'ok': False, 'message': '이미 가입된 이메일입니다.'})

    # 같은 이메일로는 1분에 한 번만 보냄
    last = EmailCode.objects.filter(email=email).order_by('-created_date').first()
    if last and timezone.now() - last.created_date < timedelta(minutes=1):
        wait = 60 - int((timezone.now() - last.created_date).total_seconds())
        return JsonResponse({'ok': False, 'message': '%d초 뒤에 다시 받을 수 있습니다.' % wait})

    code = '%06d' % secrets.randbelow(1000000)
    try:
        send_mail(
            '[Photo Blog] 회원가입 인증코드',
            'Photo Blog 회원가입 인증코드입니다.\n\n인증코드: %s\n\n5분 안에 회원가입 화면에 입력해 주세요.' % code,
            None,
            [email],
        )
    except OSError:
        return JsonResponse({'ok': False, 'message': '메일을 보내지 못했습니다. 잠시 뒤에 다시 시도해 주세요.'})
    EmailCode.objects.create(email=email, code=code)
    request.session.pop('verified_email', None)
    return JsonResponse({'ok': True, 'message': '인증코드를 보냈습니다. 메일함을 확인해 주세요.'})

@require_POST
def verify_code(request):
    email = request.POST.get('email', '').strip()
    code = request.POST.get('code', '').strip()
    last = EmailCode.objects.filter(email=email).order_by('-created_date').first()
    if last is None:
        return JsonResponse({'ok': False, 'message': '먼저 인증코드를 받아 주세요.'})

    # 유효시간 5분, 5번 틀리면 무효
    if timezone.now() - last.created_date > timedelta(minutes=5):
        return JsonResponse({'ok': False, 'message': '인증 시간이 지났습니다. 코드를 다시 받아 주세요.'})
    if last.fail_count >= 5:
        return JsonResponse({'ok': False, 'message': '5번 틀려서 이 코드는 쓸 수 없습니다. 코드를 다시 받아 주세요.'})
    if not secrets.compare_digest(last.code, code):
        last.fail_count += 1
        last.save()
        return JsonResponse({'ok': False, 'message': '인증코드가 틀렸습니다. (남은 기회 %d번)' % (5 - last.fail_count)})

    last.is_verified = True
    last.save()
    request.session['verified_email'] = email
    return JsonResponse({'ok': True, 'message': '이메일 인증이 완료되었습니다.'})

KAKAO_AUTH_URL = 'https://kauth.kakao.com/oauth/authorize'
KAKAO_TOKEN_URL = 'https://kauth.kakao.com/oauth/token'
KAKAO_USER_URL = 'https://kapi.kakao.com/v2/user/me'

def kakao_login(request):
    # 카카오 로그인 화면으로 보냄. state는 요청 위조를 막기 위한 값
    state = secrets.token_urlsafe(16)
    request.session['kakao_state'] = state
    params = urlencode({
        'response_type': 'code',
        'client_id': settings.KAKAO_REST_API_KEY,
        'redirect_uri': settings.KAKAO_REDIRECT_URI,
        'state': state,
    })
    return redirect(KAKAO_AUTH_URL + '?' + params)

def kakao_callback(request):
    if request.GET.get('error'):
        messages.error(request, '카카오 로그인을 취소했습니다.')
        return redirect('login')
    if request.GET.get('state') != request.session.pop('kakao_state', None):
        messages.error(request, '잘못된 요청입니다. 다시 시도해 주세요.')
        return redirect('login')

    try:
        # 1. 인가 코드로 토큰 받기
        res = requests.post(KAKAO_TOKEN_URL, data={
            'grant_type': 'authorization_code',
            'client_id': settings.KAKAO_REST_API_KEY,
            'client_secret': settings.KAKAO_CLIENT_SECRET,
            'redirect_uri': settings.KAKAO_REDIRECT_URI,
            'code': request.GET.get('code', ''),
        }, timeout=5)
        res.raise_for_status()
        token = res.json()['access_token']

        # 2. 토큰으로 사용자 정보 받기
        res = requests.get(KAKAO_USER_URL, headers={'Authorization': 'Bearer ' + token}, timeout=5)
        res.raise_for_status()
        info = res.json()
        kakao_id = str(info['id'])
    except (requests.RequestException, ValueError, KeyError):
        messages.error(request, '카카오 로그인에 실패했습니다. 다시 시도해 주세요.')
        return redirect('login')

    # 3. 처음이면 회원 만들기, 아니면 기존 회원으로 로그인
    profile = Profile.objects.filter(kakao_id=kakao_id).first()
    if profile is None:
        nickname = info.get('kakao_account', {}).get('profile', {}).get('nickname') or '카카오회원'
        user = User.objects.create_user('kakao_' + kakao_id)  # 비밀번호 없음 (카카오로만 로그인)
        profile = Profile.objects.create(user=user, nickname=new_nickname(nickname), kakao_id=kakao_id)
    login(request, profile.user)
    return redirect('post_list')

def new_nickname(nickname):
    # 이미 있는 닉네임이면 뒤에 숫자를 붙임
    nickname = nickname[:18]
    result = nickname
    n = 2
    while Profile.objects.filter(nickname=result).exists():
        result = '%s%d' % (nickname, n)
        n += 1
    return result

def js_test(request):
    return render(request, 'blog/js_test.html', {})

class BlogImages(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer