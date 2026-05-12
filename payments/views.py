import qrcode
import decimal
import io
import base64
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import HttpResponseBadRequest
from payments.models import payment_settings, transaction
from django.db.models import Q, Sum
from django.http import JsonResponse
from dashboard.models import PromoCode
from tradehub.services.listing import apply_time_filter, paginate_queryset

@login_required
def add_amount(request):
    # Get payment settings safely - handle case where no settings exist
    payment_setting = payment_settings.objects.all().first()
    
    if not payment_setting or not payment_setting.upi_id:
        # No payment settings configured
        if request.method == "POST":
            from django.contrib import messages
            messages.error(request, "Payment settings are not configured. Please contact support.")
            return redirect('add-amount')
        
        return render(request, 'payments/add-amount.html', {
            'error': 'payment_settings_not_configured',
            'message': 'No payment settings available. Please try again later or contact support.'
        })
    
    upi_id = payment_setting.upi_id
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
    transactions = apply_time_filter(transactions, time_filter, field_name='created_at')
    
    # Order by creation date (most recent first)
    transactions = transactions.order_by('-created_at')
    
    # Pagination
    transactions_page, paginator = paginate_queryset(transactions, page_number, per_page=10)
    
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

@login_required
def verify_payment(request, transaction_id):
    """
    Administrative/Testing view to approve a pending deposit.
    In a real app, this would be restricted to staff.
    """
    try:
        tx = transaction.objects.get(id=transaction_id, user=request.user)
        if tx.status in ['PENDING', 'REQUESTED'] and tx.transaction_type == 'DEPOSIT':
            # Approve the transaction
            tx.status = 'COMPLETED'
            # The transaction model's save() method handles add_wallet(user, amount + promo_reward)
            tx.save()
            
            messages.success(request, f"Transaction {tx.transaction_id} verified. ${tx.amount} added to your wallet.")
        else:
            messages.error(request, "This transaction cannot be verified in its current state.")
    except transaction.DoesNotExist:
        messages.error(request, "Transaction not found.")
    
    return redirect('my-transactions')