from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path("validate-promo/<str:promo_code>/", views.validate_promo_code, name="validate-promo"),
]