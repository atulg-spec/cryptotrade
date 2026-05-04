import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tradehub.settings')
django.setup()

from assets.models import MarginPosition, order as Order
from decimal import Decimal

closed_margins = MarginPosition.objects.filter(status__in=['closed', 'liquidated'], quantity=0)
for m in closed_margins:
    close_type = 'SELL' if m.side == 'LONG' else 'BUY'
    closing_orders = Order.objects.filter(
        user=m.user, stock=m.stock, is_margin=True, order_type=close_type
    ).filter(created_at__gte=m.opened_at)
    
    total_qty = sum(o.quantity for o in closing_orders)
    if total_qty > 0:
        print(f"Fixing {m.id} to {total_qty}")
        m.quantity = total_qty
        m.save()
    else:
        open_type = 'BUY' if m.side == 'LONG' else 'SELL'
        opening_orders = Order.objects.filter(
            user=m.user, stock=m.stock, is_margin=True, order_type=open_type
        ).filter(created_at__gte=m.opened_at)
        total_qty = sum(o.quantity for o in opening_orders)
        if total_qty > 0:
            print(f"Fixing {m.id} via opening to {total_qty}")
            m.quantity = total_qty
            m.save()
