from django.urls import path, include
from . import views
from assets import views as assets_views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('wallet/', views.wallet, name='wallet'),
    path('orders/', assets_views.orders_view, name='orders'),
    path('initiate-order/', assets_views.initiate_order, name='initiate_order'),
    path('portfolio/', assets_views.portfolio_view, name='portfolio'),
    path('portfolio/close-position/', assets_views.close_position, name='close_position'),
    path('watchlist/add/<str:symbol>/', assets_views.watchlist_add, name='watchlist_add'),
    path('watchlist/remove/<str:symbol>/', assets_views.watchlist_remove, name='watchlist_remove'),
    path('watchlist/search/', assets_views.stock_search, name='stock_search'),
    path("validate-promo/<str:promo_code>/", views.validate_promo_code, name="validate-promo"),
]
