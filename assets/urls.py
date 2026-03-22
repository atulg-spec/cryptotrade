from django.urls import path
from . import views
urlpatterns = [
    path('orders/', views.orders_view, name='orders'),
    path('initiate-order/', views.initiate_order, name='initiate_order'),
    path('portfolio/', views.portfolio_view, name='portfolio'),
    path('portfolio/close-position/', views.close_position, name='close_position'),
    path('watchlist/add/<str:symbol>/', views.watchlist_add, name='watchlist_add'),
    path('watchlist/remove/<str:symbol>/', views.watchlist_remove, name='watchlist_remove'),
    path('watchlist/search/', views.stock_search, name='stock_search'),
]
