from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Sum, Count, Q, F
from decimal import Decimal
import json
from datetime import datetime
from assets.models import Position
from stockmanagement.models import Stock
from django.core.serializers.json import DjangoJSONEncoder

@login_required(login_url='login')
def watchlist(request):
    stocks = Stock.objects.all().order_by('symbol')
    context = {
        'stocks': stocks,
    }
    return render(request, "stockmanagement/watchlist.html", context)
    # return render(request, "test.html", context)
