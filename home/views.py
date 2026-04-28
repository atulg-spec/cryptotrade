from django.shortcuts import render, redirect, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import random
import requests
from .models import *
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

def home(request):
    return render(request,'home/home.html')

def aboutus(request):
    return render(request,'home/aboutus.html')

def contactus(request):
    return render(request,'home/contactus.html')

def privacypolicy(request):
    return render(request,'home/privacypolicy.html')

def termsofservice(request):
    return render(request,'home/termsofservice.html')

def refundpolicy(request):
    return render(request,'home/refundpolicy.html')

def error_404_view(request, exception):
    return render(request, 'home/404.html', status=404)