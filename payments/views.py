import qrcode
import decimal
import io
import base64
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseBadRequest
from payments.models import payment_settings, transaction
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from dashboard.models import PromoCode

@login_required
def add_amount(request):
    upi_id = payment_settings.objects.all().first().upi_id
    payee_name = request.user.first_name

    if request.method == "POST":
        amount = request.POST.get("amount")
        promocode = request.POST.get("promocode")

        promo = None
        try:
            promo = PromoCode.objects.get(promo_code=promocode)
        except:
            promo = None

        if not amount:
            return HttpResponseBadRequest("Amount is required")

        # Construct UPI link
        upi_url = f"upi://pay?pa={upi_id}&pn={payee_name}&am={amount}&cu=INR"

        # Generate QR Code
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(upi_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to Base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_image_base64 = base64.b64encode(buffer.getvalue()).decode()

        context = {
            "amount": amount,
            "upi_id": upi_id,
            "payee_name": payee_name,
            "qr_code": qr_image_base64,
            "upi_url": upi_url,
            "promo": promo,
        }
        return render(request, "payments/payment.html", context)

    return render(request, 'payments/add-amount.html')


@login_required
def withdraw_amount(request):
    if request.method == "POST":
        amount = request.POST.get("amount")
        errors = []
        if not amount:
            errors.append("Please enter the amount")
        else:
            try:
                amount = decimal.Decimal(amount)
                if amount < 1:
                    errors.append("Amount must be greater than zero")
            except decimal.InvalidOperation:
                errors.append("Please enter a valid amount")
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect('profile')
        
        # Create manual payment record
        try:
            manual_payment = transaction.objects.create(
                user=request.user,
                amount = int(amount),
                transaction_type = 'WITHDRAW',
                status='REQUESTED'
            )
                        
            messages.success(request, "Your payment has been submitted for verification. We'll notify you once it's processed.")
            return redirect('my-transactions')
        
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('profile')

    return render(request, 'payments/withdraw-amount.html')


@login_required()
def save_payment_requests(request):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        transaction_id = request.POST.get('transaction_id')
        screenshot = request.FILES.get('screenshot')
        promocode = request.POST.get("promocode")

        promo = None
        try:
            promo = PromoCode.objects.get(promo_code=promocode)
        except:
            promo = None
        
        # Validate inputs
        errors = []
        
        if not amount:
            errors.append("Please enter the amount")
        else:
            try:
                amount = decimal.Decimal(amount)
                if amount < 1:
                    errors.append("Amount must be greater than zero")
            except decimal.InvalidOperation:
                errors.append("Please enter a valid amount")
        
        if not transaction_id:
            errors.append("Please provide the transaction ID")
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect('profile')
        
        # Create manual payment record
        try:
            if promo:
                reward_amount = promo.reward_amount
                if promo.promo_type == 'percentage':
                    reward_amount = decimal.Decimal((promo.reward_percentage/100))*amount
                manual_payment = transaction.objects.create(
                    user=request.user,
                    amount = amount,
                    transaction_id = transaction_id,
                    transaction_type = 'DEPOSIT',
                    screenshot = screenshot,
                    status='PENDING',
                    promo_code=promo.promo_code,
                    promo_code_reward=reward_amount,
                )
            else:
                manual_payment = transaction.objects.create(
                    user=request.user,
                    amount = amount,
                    transaction_id = transaction_id,
                    transaction_type = 'DEPOSIT',
                    screenshot = screenshot,
                    status='PENDING'
                )
                        
            messages.success(request, "Your payment has been submitted for verification. We'll notify you once it's processed.")
            return redirect('my-transactions')
        
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('profile')
    else:
        return redirect('profile')
    



@login_required
def my_transactions(request):
    # Get filter parameters
    status_filter = request.GET.get('status', 'all')
    type_filter = request.GET.get('type', 'all')
    time_filter = request.GET.get('time', 'all')
    search_query = request.GET.get('search', '')
    page_number = request.GET.get('page', 1)
    
    # Base queryset
    transactions = transaction.objects.filter(user=request.user)
    
    # Apply filters
    if status_filter != 'all':
        transactions = transactions.filter(status=status_filter)
    
    if type_filter != 'all':
        transactions = transactions.filter(transaction_type=type_filter)
    
    if search_query:
        transactions = transactions.filter(
            Q(transaction_id__icontains=search_query) |
            Q(remark__icontains=search_query)
        )
    
    # Time-based filtering
    now = timezone.now()
    if time_filter == 'today':
        today = now.date()
        transactions = transactions.filter(created_at__date=today)
    elif time_filter == 'week':
        week_ago = now - timedelta(days=7)
        transactions = transactions.filter(created_at__gte=week_ago)
    elif time_filter == 'month':
        month_ago = now - timedelta(days=30)
        transactions = transactions.filter(created_at__gte=month_ago)
    
    # Order by creation date (most recent first)
    transactions = transactions.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(transactions, 10)
    try:
        transactions_page = paginator.page(page_number)
    except PageNotAnInteger:
        transactions_page = paginator.page(1)
    except EmptyPage:
        transactions_page = paginator.page(paginator.num_pages)
    
    # Statistics
    total_transactions = transaction.objects.filter(user=request.user).count()
    total_deposits = transaction.objects.filter(
        user=request.user, 
        transaction_type='DEPOSIT',
        status='COMPLETED'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    total_withdrawals = transaction.objects.filter(
        user=request.user, 
        transaction_type='WITHDRAW',
        status='COMPLETED'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    pending_transactions = transaction.objects.filter(
        user=request.user,
        status__in=['PENDING', 'REQUESTED']
    ).count()
    
    context = {
        'transactions': transactions_page,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'time_filter': time_filter,
        'search_query': search_query,
        'total_transactions': total_transactions,
        'total_deposits': total_deposits,
        'total_withdrawals': total_withdrawals,
        'pending_transactions': pending_transactions,
        'page_range': paginator.get_elided_page_range(number=transactions_page.number, on_each_side=1, on_ends=1)
    }
    
    return render(request, 'dashboard/my-transactions.html', context)

@login_required
def cancel_transaction(request, transaction_id):
    if request.method == 'POST':
        try:
            transaction = transaction.objects.get(id=transaction_id, user=request.user)
            if transaction.status in ['PENDING', 'REQUESTED']:
                transaction.status = 'CANCELLED'
                transaction.save()
                return JsonResponse({
                    'success': True,
                    'message': 'Transaction cancelled successfully'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Cannot cancel transaction in current status'
                })
        except transaction.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Transaction not found'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    })