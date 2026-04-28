# accounts/urls.py
from django.urls import path, include
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.handlelogout, name='logout'),

    path('profile/', views.profile, name='profile'),
    path('profile/update/', views.update_profile, name='update_profile'),

    path('update-user-location/', views.UpdateUserLocationView.as_view(), name='update_user_location'),
]