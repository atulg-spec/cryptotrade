# accounts/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
import json
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from assets.models import order as Order
from django.db import models
from django.utils import timezone
from django.contrib.auth import login, logout, authenticate, get_user_model
from .forms import CustomUserCreationForm
from django.contrib.auth.forms import AuthenticationForm
from dashboard.models import SiteSettings

UserModel = get_user_model()


def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            site_settings = SiteSettings.objects.first()
            site_name = site_settings.site_name if site_settings else 'TradeHub'
            messages.success(request, f'Registration successful! Welcome to {site_name}.')
            return redirect('profile')  # Replace with your desired redirect
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            identifier = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            user = authenticate(request, username=identifier, password=password)

            if user is None:
                try:
                    user_obj = UserModel.objects.get(username__iexact=identifier)
                    user = authenticate(request, username=user_obj.email, password=password)
                except UserModel.DoesNotExist:
                    user = None

            if user is None and '@' in identifier:
                try:
                    user_obj = UserModel.objects.get(email__iexact=identifier)
                    user = authenticate(request, username=user_obj.email, password=password)
                except UserModel.DoesNotExist:
                    user = None

            if user is not None:
                login(request, user)
                display_name = user.username or user.email
                messages.success(request, f'Welcome back, {display_name}!')
                next_url = request.GET.get('next', 'dashboard')  # Replace with your dashboard URL name
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    
    return render(request, 'accounts/login.html', {'form': form})


class UpdateUserLocationView(View):
    @method_decorator(login_required)  # Ensures that the user is logged in
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            user = request.user  # Get the logged-in user

            # Update the user model with the new location data
            user.region_name = data.get('region_name', user.region_name)
            user.city = data.get('city', user.city)
            user.zip_code = data.get('zip_code', user.zip_code)
            user.lat = data.get('lat', user.lat)
            user.lon = data.get('lon', user.lon)
            user.timezone = data.get('timezone', user.timezone)
            user.isp = data.get('isp', user.isp)

            user.save()  # Save the changes to the user model

            return JsonResponse({"message": "User data updated successfully"}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


@login_required
def profile(request):
    user = request.user
    
    # Get user statistics
    total_orders = Order.objects.filter(user=user).count()
    completed_orders = Order.objects.filter(user=user, status='completed').count()
    total_investment = Order.objects.filter(
        user=user, 
        status='completed',
        order_type='BUY'
    ).aggregate(total=models.Sum('amount'))['total'] or 0
    
    # Get recent orders for activity feed
    recent_orders = Order.objects.filter(user=user).select_related('stock').order_by('-created_at')[:5]
    
    # Calculate account age
    account_age = timezone.now() - user.date_joined
    
    context = {
        'user': user,
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'total_investment': total_investment,
        'recent_orders': recent_orders,
        'account_age_days': account_age.days,
    }
    
    return render(request, 'accounts/profile.html', context)

@login_required
def update_profile(request):
    if request.method == 'POST':
        user = request.user
        
        # Update basic profile information
        user.phone_number = request.POST.get('phone_number', user.phone_number)
        user.region_name = request.POST.get('region_name', user.region_name)
        user.city = request.POST.get('city', user.city)
        user.zip_code = request.POST.get('zip_code', user.zip_code)

        user.bank_account_name = request.POST.get('bank_account_name', user.bank_account_name)
        user.bank_account_number = request.POST.get('bank_account_number', user.bank_account_number)
        user.upi_id = request.POST.get('upi_id', user.upi_id)
        user.ifsc_code = request.POST.get('ifsc_code', user.ifsc_code)
        
        try:
            user.save()
            messages.success(request, 'Profile updated successfully!')
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
        
        return redirect('profile')
    
    return redirect('profile')

def handlelogout(request):
    logout(request)
    messages.success(request,"Logged out Successfully")
    print('here')
    return redirect('login')