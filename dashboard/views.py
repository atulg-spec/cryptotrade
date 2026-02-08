from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Sum, Count, Q, F
from decimal import Decimal
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import PromoCode
from assets.models import Position
from stockmanagement.models import Stock
from django.core.serializers.json import DjangoJSONEncoder

@login_required(login_url='login')
def dashboard(request):
    positions = Position.objects.filter(user=request.user).select_related('stock')
    open_positions = Position.objects.filter(user=request.user, is_closed=False)
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
    context = {
        'portfolio_value': portfolio_value,
        'positions': positions,
        'unrealised_pnl': unrealised_pnl,
        'holdings': open_positions.__len__(),
        'open_positions': open_positions,
        'chart_data': chart_data,
        'chart_data_json': chart_data_json,
    }

    return render(request, "dashboard/dashboard.html", context)


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
