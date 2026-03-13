from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/watchlist/$", consumers.WatchlistConsumer.as_asgi()),
    # Per-user events: order status changes, portfolio updates, etc.
    re_path(r"ws/user-events/$", consumers.UserEventsConsumer.as_asgi()),
]
