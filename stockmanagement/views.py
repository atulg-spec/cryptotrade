from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Sum, Count, Q, F
from decimal import Decimal
import json
from datetime import datetime
from assets.models import Position
from stockmanagement.models import Stock
from django.core.serializers.json import DjangoJSONEncoder

@login_required(login_url='login')
def watchlist(request):
    stocks = Stock.objects.all().order_by('-current_price')
    context = {
        'stocks': stocks,
    }
    return render(request, "stockmanagement/watchlist.html", context)

@login_required
def get_prices(request):
    stocks = Stock.objects.all()
    updates = [
        {
            'id': s.id,
            'symbol': s.symbol,
            'current_price': float(s.current_price),
            'percentage_change': float(s.percentage_change),
            'price_change': float(s.price_change),
            'volume': float(s.quote_volume_24h)
        }
        for s in stocks
    ]
    return JsonResponse({'updates': updates})
