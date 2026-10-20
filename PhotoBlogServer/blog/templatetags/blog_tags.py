from django import template

register = template.Library()

@register.filter
def nickname(user):
    # 닉네임이 없는 계정(관리자 등)은 아이디를 보여 줌
    if hasattr(user, 'profile'):
        return user.profile.nickname
    return user.username
