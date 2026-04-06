from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Sum, Count, Q, F
from decimal import Decimal
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import PromoCode
from assets.models import Position, order as Order, Watchlist
from stockmanagement.models import Stock
from django.core.serializers.json import DjangoJSONEncoder
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.utils import timezone
import datetime


@login_required(login_url='login')
def wallet(request):
    """Wallet page view with balance and transaction information."""
    # Get user's wallet balance
    wallet_balance = float(request.user.wallet)
    
    # Get open positions and invested amount
    open_positions = Position.objects.filter(user=request.user, is_closed=False)
    invested_amount = sum(
        float(pos.buy_price) * float(pos.quantity) for pos in open_positions
    )
    
    # Calculate total equity
    current_value = sum(
        float(pos.stock.current_price) * float(pos.quantity) for pos in open_positions
    )
    total_equity = wallet_balance + current_value
    
    # Calculate total P&L
    total_pnl = current_value - invested_amount if invested_amount > 0 else 0
    
    context = {
        'wallet_balance': wallet_balance,
        'invested_amount': invested_amount,
        'open_positions_count': open_positions.count(),
        'total_equity': total_equity,
        'total_pnl': total_pnl,
    }
    
    return render(request, 'dashboard/wallet.html', context)

@login_required(login_url='login')
def dashboard(request):
    open_positions = (
        Position.objects
        .filter(user=request.user, is_closed=False, quantity__gt=0)
        .select_related('stock')
        .order_by('-created_at')
    )
    positions = (
        Position.objects
        .filter(user=request.user)
        .select_related('stock')
        .order_by('-created_at')
    )

    watchlist_items = Watchlist.objects.filter(user=request.user).select_related('stock')
    favorites = []
    for item in watchlist_items:
        item.stock.is_favorite = True
        favorites.append(item.stock)

    portfolio_value = Decimal('0')
    portfolio_purchased_value = Decimal('0')
    labels = [pos.stock.name for pos in open_positions]
    data = [pos.quantity * pos.buy_price for pos in open_positions]  # investment value per stock

    chart_data = {
        'labels': labels,
        'data': data,
    }

    chart_data_json = json.dumps(chart_data, cls=DjangoJSONEncoder)

    for position in open_positions:
        portfolio_value += Decimal(position.stock.current_price) * Decimal(position.quantity)
        portfolio_purchased_value += Decimal(str(position.buy_price)) * Decimal(position.quantity)

    unrealised_pnl = float(portfolio_value - portfolio_purchased_value) if open_positions else 0
    total_equity = float(request.user.wallet) + float(portfolio_value)
    invested_amount = float(portfolio_purchased_value)
    today_pnl = float(unrealised_pnl)
    daily_return_pct = (today_pnl / invested_amount * 100) if invested_amount > 0 else 0
    pnl_history_data = [] 
    pnl_history_labels = []
    recent_orders = Order.objects.filter(user=request.user).order_by('-created_at')[:50]

    context = {
        'favorites': favorites,
        'portfolio_value': portfolio_value,
        'positions': positions,
        'unrealised_pnl': unrealised_pnl,
        'holdings': open_positions.count(),
        'open_positions': open_positions,
        'chart_data': chart_data,
        'chart_data_json': chart_data_json,
        'wallet': request.user.wallet,
        'total_equity': total_equity,
        'invested_amount': invested_amount,
        'today_pnl': today_pnl,
        'daily_return_pct': daily_return_pct,
        'pnl_history_data': json.dumps(pnl_history_data, cls=DjangoJSONEncoder),
        'pnl_history_labels': json.dumps(pnl_history_labels, cls=DjangoJSONEncoder),
        'recent_orders': recent_orders,
    }

    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    is_mobile = any(keyword in user_agent for keyword in ['mobile', 'android', 'iphone', 'ipad', 'webos', 'opera mini', 'iemobile'])
    
    template_name = "dashboard/dashboard_mobile.html" if is_mobile else "dashboard/dashboard_desktop.html"
    
    return render(request, template_name, context)


@csrf_exempt
def validate_promo_code(request, promo_code):
    try:
        promo = PromoCode.objects.get(promo_code=promo_code)
        if promo.promo_type == 'amount':
            return JsonResponse({
                "success": True,
                "message": "Promo code is valid.",
                "promo_code": promo.promo_code,
                "reward_amount": promo.reward_amount,
            }, status=200)
        else:
            return JsonResponse({
                "success": True,
                "message": "Promo code is valid.",
                "promo_code": promo.promo_code,
                "reward_amount": f'{promo.reward_percentage}%',
            }, status=200)

    except PromoCode.DoesNotExist:
        return JsonResponse({
            "success": False,
            "message": "Invalid promo code.",
        }, status=404)


