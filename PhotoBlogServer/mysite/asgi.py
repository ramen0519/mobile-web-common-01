"""
ASGI config for mysite project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

django_asgi_app = get_asgi_application()

from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
import blog.routing

application = ProtocolTypeRouter({
    # CSS 같은 정적 파일도 장고가 직접 보냄 (wsgi 파일의 StaticFilesHandler와 같은 역할)
    'http': ASGIStaticFilesHandler(django_asgi_app),
    # 채팅: 로그인 정보를 읽고, 허용된 주소에서 온 연결만 받음
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(URLRouter(blog.routing.websocket_urlpatterns))
    ),
})
