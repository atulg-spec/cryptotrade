from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import order as Order


@receiver(post_save, sender=Order)
def broadcast_order_update(sender, instance, created, **kwargs):
    """
    Broadcast order status/values in real time to the owning user.
    """
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    group_name = f"user_{instance.user_id}"

    payload = {
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
        {"type": "user_event", "payload": payload},
    )

