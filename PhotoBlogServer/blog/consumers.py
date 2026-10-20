import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from django.utils import timezone
from .models import ChatMessage
from .templatetags.blog_tags import nickname

class ChatConsumer(WebsocketConsumer):
    group_name = 'chat'
    users = {}  # 접속 중인 사람 {채널 이름: 닉네임}

    def connect(self):
        user = self.scope['user']
        # 로그인한 사람만 채팅 가능
        if not user.is_authenticated:
            self.close()
            return
        self.nickname = nickname(user)
        async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)
        self.accept()
        # 다른 탭으로 이미 들어와 있으면 입장 안내 없이 접속자 목록만 갱신
        first = self.nickname not in ChatConsumer.users.values()
        ChatConsumer.users[self.channel_name] = self.nickname
        self.send_group({'type': 'join' if first else 'users', 'nickname': self.nickname})

    def disconnect(self, close_code):
        if self.channel_name in ChatConsumer.users:
            del ChatConsumer.users[self.channel_name]
            async_to_sync(self.channel_layer.group_discard)(self.group_name, self.channel_name)
            gone = self.nickname not in ChatConsumer.users.values()
            self.send_group({'type': 'leave' if gone else 'users', 'nickname': self.nickname})

    def receive(self, text_data):
        try:
            text = json.loads(text_data)['text'].strip()[:500]
        except (ValueError, KeyError, TypeError, AttributeError):
            return
        if not text:
            return
        user = self.scope['user']
        message = ChatMessage.objects.create(user=user, text=text)
        self.send_group({
            'type': 'message',
            'user_id': user.pk,
            'nickname': self.nickname,
            'text': text,
            'time': timezone.localtime(message.created_date).strftime('%H:%M'),
        })

    def send_group(self, data):
        # 방에 있는 모든 사람에게 보냄 (접속자 목록도 같이)
        data['users'] = sorted(set(ChatConsumer.users.values()))
        async_to_sync(self.channel_layer.group_send)(self.group_name, {'type': 'chat.event', 'data': data})

    def chat_event(self, event):
        self.send(text_data=json.dumps(event['data']))
