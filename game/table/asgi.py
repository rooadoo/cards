import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'table.settings')
from django.core.asgi import get_asgi_application
asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from .routing import websocket_urlpatterns


application = ProtocolTypeRouter({
  "http": asgi_app,
  "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
