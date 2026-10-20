from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Post, Profile

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('title', 'text',)

class SignupForm(UserCreationForm):
    nickname = forms.CharField(max_length=20)
    email = forms.EmailField()

    class Meta(UserCreationForm.Meta):
        fields = ('username', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean_username(self):
        username = super().clean_username()  # 이미 있는 아이디면 오류를 남기고 None을 돌려줌
        # kakao_로 시작하는 아이디는 카카오 로그인 회원용
        if username and username.lower().startswith('kakao_'):
            raise forms.ValidationError('kakao_로 시작하는 아이디는 쓸 수 없습니다.')
        return username

    def clean_nickname(self):
        nickname = self.cleaned_data['nickname']
        if Profile.objects.filter(nickname=nickname).exists():
            raise forms.ValidationError('이미 사용 중인 닉네임입니다.')
        return nickname

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('이미 가입된 이메일입니다.')
        return email
