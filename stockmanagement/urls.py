from django.urls import path, include
from . import views

urlpatterns = [
    path('watchlist/', views.watchlist, name='watchlist'),
]