from django.urls import path
from .views import *

urlpatterns = [
    path('', home, name='home'),
    path('contact/', contactus, name='contactus'),
    # path('aboutus/', aboutus, name='aboutus'),
    # path('privacypolicy/', privacypolicy, name='privacypolicy'),
    # path('termsofservice/', termsofservice, name='termsofservice'),
    # path('refundpolicy/', refundpolicy, name='refundpolicy'),
]