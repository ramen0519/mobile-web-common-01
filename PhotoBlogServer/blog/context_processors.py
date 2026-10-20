def notifications(request):
    # 상단 메뉴에 보여 줄 안 읽은 알림 개수
    if request.user.is_authenticated:
        return {'unread_count': request.user.notifications.filter(is_read=False).count()}
    return {}
