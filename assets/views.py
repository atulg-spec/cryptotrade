from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from assets.utils import place_order
from stockmanagement.models import Stock
from django.contrib import messages
from django.db.models import Q, Sum
from django.utils import timezone
from .models import order as Order
from .models import Position, MarginPosition
from decimal import Decimal, InvalidOperation
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.urls import reverse
from assets.models import Watchlist
from tradehub.services.listing import apply_time_filter, paginate_queryset
from assets.services.margin_service import (
    execute_margin_trade,
    close_margin_position,
)

@login_required
def orders_view(request):
    # Get filter parameters
    status_filter = request.GET.get('status', 'all')
    order_type_filter = request.GET.get('type', 'all')
    time_filter = request.GET.get('time', 'all')
    search_query = request.GET.get('search', '')
    page_number = request.GET.get('page', 1)
    
    # Base queryset
    orders = Order.objects.filter(user=request.user).select_related('stock')
    
    # Apply filters
    if status_filter != 'all':
        orders = orders.filter(status=status_filter)
    
    if order_type_filter != 'all':
        orders = orders.filter(order_type=order_type_filter)
    
    if search_query:
        orders = orders.filter(
            Q(stock__symbol__icontains=search_query) |
            Q(stock__name__icontains=search_query)
        )
    
    # Time-based filtering
    orders = apply_time_filter(orders, time_filter, field_name='created_at')
    
    # Order by creation date (most recent first)
    orders = orders.order_by('-created_at')
    
    # Pagination
    orders_page, paginator = paginate_queryset(orders, page_number, per_page=10)
    
    # Statistics
    total_orders = Order.objects.filter(user=request.user).count()
    total_investment = Order.objects.filter(
        user=request.user, 
        status='completed',
        order_type='BUY'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    context = {
        'orders': orders_page,
        'status_filter': status_filter,
        'order_type_filter': order_type_filter,
        'time_filter': time_filter,
        'search_query': search_query,
        'total_orders': total_orders,
        'total_investment': total_investment,
        'page_range': paginator.get_elided_page_range(number=orders_page.number, on_each_side=1, on_ends=1)
    }
    
    return render(request, 'dashboard/orders.html', context)


@login_required
def initiate_order(request):
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    if request.method != 'POST':
        if is_ajax:
            return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)
        return redirect('watchlist')

    symbol = (request.POST.get("symbol") or "").strip().upper()
    order_type = (request.POST.get("order_type") or "BUY").upper()

    stock = Stock.objects.filter(symbol=symbol).first()
    if not stock:
        return _order_response(request, False, "Selected stock could not be found.", is_ajax)

    # BUY: primary input is investment amount (value-based trading)
    # SELL: primary input is quantity (supports fractional lots)
    amount_raw = request.POST.get("amount")
    quantity_raw = request.POST.get("quantity")

    try:
        if order_type == "BUY":
            amount = Decimal(str(amount_raw))
            if amount <= 0:
                raise InvalidOperation

            price = stock.current_price or Decimal("0")
            if price <= 0:
                return _order_response(
                    request,
                    False,
                    "Unable to place order. Invalid stock price.",
                    is_ajax,
                )

            quantity = amount / price
        else:
            quantity = Decimal(str(quantity_raw))
            if quantity <= 0:
                raise InvalidOperation
            amount = None  # derived inside place_order
    except (InvalidOperation, TypeError):
        error_msg = (
            "Please enter a valid investment amount."
            if order_type == "BUY"
            else "Please enter a valid quantity."
        )
        return _order_response(request, False, error_msg, is_ajax)

    status, response = place_order(request.user, stock, quantity, order_type, amount=amount)
    return _order_response(request, status, response, is_ajax)
    

def _order_response(request, success, message, is_ajax):
    redirect_url = reverse('orders')
    if is_ajax:
        status_code = 200 if success else 400
        return JsonResponse({
            'success': success,
            'message': message,
            'redirect_url': redirect_url if success else ''
        }, status=status_code)

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)
    return redirect('orders')


@login_required
def portfolio_view(request):
    # Get all positions for the current user
    positions = Position.objects.filter(user=request.user).select_related('stock')
    
    # Calculate portfolio metrics
    open_positions = positions.filter(is_closed=False)
    closed_positions = positions.filter(is_closed=True)
    
    labels = [pos.stock.name for pos in open_positions]
    data = [pos.quantity * pos.buy_price for pos in open_positions]  # investment value per stock

    chart_data = {
        'labels': labels,
        'data': data,
    }

    chart_data_json = json.dumps(chart_data, cls=DjangoJSONEncoder)


    # Calculate total portfolio value and P&L
    total_investment = sum(position.quantity * position.buy_price for position in open_positions)
    current_value = 0
    total_realised_pnl = sum(position.realised_pnl for position in closed_positions)
    
    # Calculate today's P&L (positions traded today)
    today = timezone.now().date()
    today_positions = positions.filter(last_traded_datetime__date=today)
    today_pnl = sum(position.realised_pnl for position in today_positions)

    # Margin Positions logic
    margin_positions = MarginPosition.objects.filter(user=request.user)
    closed_margin_positions = margin_positions.filter(status__in=[MarginPosition.STATUS_CLOSED, MarginPosition.STATUS_LIQUIDATED])
    today_margin_positions = closed_margin_positions.filter(closed_at__date=today)
    
    total_realised_pnl += sum(pos.realised_pnl for pos in closed_margin_positions)
    today_pnl += sum(pos.realised_pnl for pos in today_margin_positions)
    
    # Update counts to include margin
    open_positions_count = open_positions.count() + margin_positions.filter(status=MarginPosition.STATUS_OPEN).count()
    closed_positions_count = closed_positions.count() + closed_margin_positions.count()

    # Group positions by stock for summary
    position_summary = {}
    for position in open_positions:
        stock_symbol = position.stock.symbol
        if stock_symbol not in position_summary:
            position_summary[stock_symbol] = {
                'stock': position.stock,
                'total_quantity': position.quantity,
                'avg_buy_price': position.buy_price,
                'total_investment': position.buy_price * position.quantity,
                'current_value': Decimal(position.quantity) * Decimal(position.stock.current_price),
                'unrealised_pnl': Decimal((position.quantity*position.stock.current_price))-Decimal((position.buy_price*position.quantity)),
                'type': 'spot'
            }
            
    # Include margin open positions in the summary table
    for mpos in margin_positions.filter(status=MarginPosition.STATUS_OPEN):
        stock_symbol = mpos.stock.symbol
        if stock_symbol not in position_summary:
            position_summary[stock_symbol] = {
                'stock': mpos.stock,
                'total_quantity': mpos.quantity,
                'avg_buy_price': mpos.entry_price,
                'total_investment': mpos.margin_used, # Use margin as investment
                'current_value': mpos.position_size, # Or something else
                'unrealised_pnl': mpos.unrealised_pnl(mpos.stock.current_price),
                'type': 'margin'
            }
        else:
            # Simple addition for demo purposes if same stock has both
            position_summary[stock_symbol]['total_quantity'] += mpos.quantity
            position_summary[stock_symbol]['total_investment'] += mpos.margin_used
            position_summary[stock_symbol]['unrealised_pnl'] += mpos.unrealised_pnl(mpos.stock.current_price)
        
    
    # Calculate average buy price and P&L for each stock
    for symbol, summary in position_summary.items():
        summary['pnl_percentage'] = (Decimal(summary['unrealised_pnl']) / Decimal(summary['total_investment']) * 100) if summary['total_investment'] > 0 else 0
        if summary.get('type') != 'margin':
            current_value += summary['current_value']
    
    total_unrealised_pnl = current_value - total_investment
    
    context = {
        'positions': positions,
        'open_positions': open_positions,
        'closed_positions': closed_positions,
        'position_summary': position_summary,
        'total_investment': total_investment,
        'current_value': current_value,
        'total_unrealised_pnl': total_unrealised_pnl,
        'total_realised_pnl': total_realised_pnl,
        'today_pnl': today_pnl,
        'total_positions': positions.count() + margin_positions.count(),
        'open_positions_count': open_positions_count,
        'closed_positions_count': closed_positions_count,
        'chart_data_json': chart_data_json,
        'chart_data': chart_data,
    }
    
    return render(request, 'dashboard/portfolio.html', context)


@login_required
def close_position(request):
    if request.method != 'POST':
        return redirect('portfolio')

    stock_id = request.POST.get('stock_id')
    quantity_raw = request.POST.get('quantity')

    try:
        quantity = Decimal(str(quantity_raw))
    except (TypeError, InvalidOperation):
        messages.error(request, 'Unable to close the position. Invalid quantity provided.')
        return redirect('portfolio')

    if quantity <= 0:
        messages.error(request, 'Position quantity must be greater than zero.')
        return redirect('portfolio')

    stock = Stock.objects.filter(id=stock_id).first()
    if not stock:
        messages.error(request, 'Stock not found.')
        return redirect('portfolio')

    success, response = place_order(request.user, stock, quantity, 'SELL')
    if success:
        messages.success(request, response)
    else:
        messages.error(request, response)

    return redirect('portfolio')




@login_required
def watchlist_add(request, symbol):
    """
    API endpoint to add a stock to the user's watchlist.
    """
    symbol = symbol.strip().upper()
    try:
        stock = Stock.objects.get(symbol=symbol)
        Watchlist.objects.get_or_create(user=request.user, stock=stock)
        return JsonResponse({'success': True, 'message': f'{symbol} added to watchlist.'})
    except Stock.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Stock not found.'}, status=404)

@login_required
def watchlist_remove(request, symbol):
    """
    API endpoint to remove a stock from the user's watchlist.
    """
    symbol = symbol.strip().upper()
    try:
        stock = Stock.objects.get(symbol=symbol)
        Watchlist.objects.filter(user=request.user, stock=stock).delete()
        return JsonResponse({'success': True, 'message': f'{symbol} removed from watchlist.'})
    except Stock.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Stock not found.'}, status=404)

@login_required
def stock_search(request):
    """
    API endpoint for real-time stock search.
    """
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': []})

    stocks = Stock.objects.filter(
        Q(symbol__icontains=query) | Q(name__icontains=query)
    ).values('symbol', 'name', 'current_price', 'percentage_change')[:10]

    # Check which stocks are already in the user's watchlist
    watchlist_symbols = set(Watchlist.objects.filter(user=request.user).values_list('stock__symbol', flat=True))
    
    results = []
    for s in stocks:
        results.append({
            'symbol': s['symbol'],
            'name': s['name'],
            'price': float(s['current_price']),
            'change': float(s['percentage_change']),
            'is_in_watchlist': s['symbol'] in watchlist_symbols
        })

    return JsonResponse({'results': results})


# ────────────────────────────────────────────────────────────────────────────
#  MARGIN ORDER ENDPOINTS
# ────────────────────────────────────────────────────────────────────────────

@login_required
def initiate_margin_order(request):
    """
    Open or add to a margin (leveraged) position.

    POST params
    -----------
    symbol       : str   e.g. 'BTCUSDT'
    side         : str   'LONG' | 'SHORT'
    margin_amount: float collateral from wallet
    leverage     : int   1–125
    """
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST required.'}, status=405)

    symbol       = (request.POST.get('symbol') or '').strip().upper()
    side         = (request.POST.get('side') or 'LONG').upper()
    leverage_raw = request.POST.get('leverage', '10')
    margin_raw   = request.POST.get('margin_amount')

    stock = Stock.objects.filter(symbol=symbol).first()
    if not stock:
        return JsonResponse({'success': False, 'message': 'Stock not found.'}, status=404)

    try:
        margin_amount = Decimal(str(margin_raw))
        leverage      = int(leverage_raw)
        if margin_amount <= 0 or leverage < 1:
            raise InvalidOperation
    except (InvalidOperation, TypeError, ValueError):
        return JsonResponse(
            {'success': False, 'message': 'Invalid margin amount or leverage.'}, status=400
        )

    success, message = execute_margin_trade(
        user=request.user,
        stock=stock,
        margin_amount=margin_amount,
        leverage=leverage,
        side=side,
    )

    status_code = 200 if success else 400
    return JsonResponse({'success': success, 'message': message}, status=status_code)


@login_required
def close_margin_order(request):
    """
    Close (fully or partially) an open margin position.

    POST params
    -----------
    symbol    : str
    side      : 'LONG' | 'SHORT'
    quantity  : float  (optional — omit for full close)
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST required.'}, status=405)

    symbol       = (request.POST.get('symbol') or '').strip().upper()
    side         = (request.POST.get('side') or 'LONG').upper()
    quantity_raw = request.POST.get('quantity')  # optional

    stock = Stock.objects.filter(symbol=symbol).first()
    if not stock:
        return JsonResponse({'success': False, 'message': 'Stock not found.'}, status=404)

    close_qty = None
    if quantity_raw:
        try:
            close_qty = Decimal(str(quantity_raw))
            if close_qty <= 0:
                raise InvalidOperation
        except (InvalidOperation, TypeError, ValueError):
            return JsonResponse({'success': False, 'message': 'Invalid quantity.'}, status=400)

    success, message = close_margin_position(
        user=request.user,
        stock=stock,
        side=side,
        close_qty=close_qty,
    )

    status_code = 200 if success else 400
    return JsonResponse({'success': success, 'message': message}, status=status_code)


@login_required
def margin_positions_api(request):
    """
    Return current open margin positions as JSON (used by the dashboard
    to populate the Margin tab without a full page reload).
    """
    positions = (
        MarginPosition.objects
        .filter(user=request.user, status=MarginPosition.STATUS_OPEN)
        .select_related('stock')
    )

    data = []
    for pos in positions:
        current_price = float(pos.stock.current_price)
        entry = float(pos.entry_price)
        qty = float(pos.quantity)
        lev = pos.leverage
        margin = float(pos.margin_used)
        liq = float(pos.liquidation_price)

        if pos.side == MarginPosition.LONG:
            upnl = (current_price - entry) * qty
        else:
            upnl = (entry - current_price) * qty

        roe_pct = (upnl / margin * 100) if margin > 0 else 0

        data.append({
            'id': pos.id,
            'symbol': pos.stock.symbol,
            'side': pos.side,
            'leverage': lev,
            'margin_used': round(margin, 2),
            'position_size': float(pos.position_size),
            'quantity': qty,
            'entry_price': entry,
            'current_price': current_price,
            'liquidation_price': liq,
            'unrealised_pnl': round(upnl, 2),
            'roe_pct': round(roe_pct, 2),
            'opened_at': pos.opened_at.isoformat(),
        })

    return JsonResponse({'positions': data, 'wallet_balance': float(request.user.wallet)})

