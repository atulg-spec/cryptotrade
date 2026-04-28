from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from decimal import Decimal

from .models import order as Order
from .models import Position
from stockmanagement.models import Stock


def send_portfolio_update_to_user(user_id):
    """
    Helper function to send portfolio update to a specific user.
    
    Calculates current portfolio state and broadcasts it.
    """
    from accounts.models import CustomUser as User
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return
    
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    
    group_name = f"user_{user_id}"
    
    # Calculate portfolio data
    open_positions = Position.objects.filter(user=user, is_closed=False).select_related('stock')
    
    positions_data = []
    total_investment = Decimal('0')
    total_current_value = Decimal('0')
    
    for pos in open_positions:
        current_price = pos.stock.current_price
        quantity = Decimal(str(pos.quantity))
        buy_price = Decimal(str(pos.buy_price))
        
        current_value = quantity * current_price
        investment = quantity * buy_price
        unrealised_pnl = current_value - investment
        pnl_percentage = (unrealised_pnl / investment * 100) if investment > 0 else Decimal('0')
        
        positions_data.append({
            'stock_id': pos.stock_id,
            'symbol': pos.stock.symbol,
            'name': pos.stock.name,
            'quantity': float(quantity),
            'avg_buy_price': float(buy_price),
            'current_price': float(current_price),
            'current_value': float(current_value),
            'unrealised_pnl': float(unrealised_pnl),
            'pnl_percentage': float(pnl_percentage),
        })
        
        total_investment += investment
        total_current_value += current_value
    
    total_unrealised_pnl = total_current_value - total_investment
    
    payload = {
        "event": "portfolio_update",
        "positions": positions_data,
        "total_investment": float(total_investment),
        "total_current_value": float(total_current_value),
        "total_unrealised_pnl": float(total_unrealised_pnl),
        "wallet_balance": float(user.wallet),
        "total_equity": float(user.wallet) + float(total_current_value),
        "positions_count": open_positions.count(),
    }
    
    async_to_sync(channel_layer.group_send)(
        group_name,
        {"type": "user_event", "payload": payload},
    )


@receiver(post_save, sender=Order)
def broadcast_order_update(sender, instance, created, **kwargs):
    """
    Broadcast order status/values in real time to the owning user.
    Also triggers portfolio update when order is completed.
    """
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    group_name = f"user_{instance.user_id}"

    # Send order update
    order_payload = {
        "event": "order_update",
        "order_id": instance.id,
        "status": instance.status,
        "symbol": instance.stock.symbol,
        "order_type": instance.order_type,
        "amount": float(instance.amount),
        "price": float(instance.price),
        "quantity": float(instance.quantity),
        "created_at": instance.created_at.isoformat() if instance.created_at else None,
    }

    async_to_sync(channel_layer.group_send)(
        group_name,
        {"type": "user_event", "payload": order_payload},
    )
    
    # If order is completed, also send portfolio update
    if instance.status == 'completed':
        send_portfolio_update_to_user(instance.user_id)


@receiver(post_save, sender=Position)
def broadcast_position_update(sender, instance, created, **kwargs):
    """
    Broadcast position changes in real time to the owning user.
    Triggers portfolio update whenever a position is created, updated, or closed.
    """
    send_portfolio_update_to_user(instance.user_id)


@receiver(post_save, sender=Stock)
def broadcast_stock_price_update(sender, instance, **kwargs):
    """
    Broadcast stock price updates to all users who hold this stock.
    This ensures portfolio values update when stock prices change.
    """
    # Find all users with open positions in this stock
    positions = Position.objects.filter(stock=instance, is_closed=False).select_related('user')
    user_ids = set(positions.values_list('user_id', flat=True))
    
    for user_id in user_ids:
        send_portfolio_update_to_user(user_id)

