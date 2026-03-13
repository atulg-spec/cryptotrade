from django.db import models
from accounts.models import CustomUser as User
from stockmanagement.models import Stock
from django.utils import timezone
import datetime
from decimal import Decimal

# Create your models here.
class Position(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    # Support fractional quantities using Decimal for precision
    quantity = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal("0"))
    last_traded_quantity = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal("0"))
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    buy_price = models.DecimalField(max_digits=12, decimal_places=5, default=Decimal("0.00"))
    sell_price = models.DecimalField(max_digits=12, decimal_places=5, default=Decimal("0.00"))
    realised_pnl = models.DecimalField(max_digits=20, decimal_places=5, default=Decimal("0.00"))
    last_traded_datetime = models.DateTimeField(default=timezone.now)
    is_closed = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Position"
        verbose_name_plural = "Positions"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if self.quantity == 0:
            self.is_closed = True
            self.unrealised_pnl = (Decimal(self.sell_price) - Decimal(self.buy_price)) * Decimal(
                self.last_traded_quantity
            )
            self.realised_pnl = (Decimal(self.realised_pnl) + self.unrealised_pnl).quantize(Decimal("0.01"))
            self.unrealised_pnl = Decimal("0.00")

        self.last_traded_datetime = datetime.datetime.now()
        if self.last_traded_quantity < 0:
            self.last_traded_quantity = self.last_traded_quantity * -1
        # Normalize prices to 2 decimal places for display/aggregation
        self.buy_price = Decimal(self.buy_price).quantize(Decimal("0.01"))
        self.sell_price = Decimal(self.sell_price).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)
    def __str__(self):
      return self.stock.name


class order(models.Model):
    order_status = [
        ('initiated', 'initiated'),
        ('pending', 'pending'),
        ('completed', 'completed'),
        ('cancelled', 'cancelled'),
        ('failed', 'failed'),
    ]

    order_type = [
        ('BUY', 'BUY'),
        ('SELL', 'SELL'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=12, decimal_places=5, default=Decimal("0.00"))
    # Support fractional order quantities
    quantity = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal("0"))
    status = models.CharField(max_length=10, choices=order_status, default="pending")
    amount = models.DecimalField(max_digits=20, decimal_places=5, default=Decimal("0.00"))
    order_type = models.CharField(choices=order_type, max_length=5, default="")
    charges = models.DecimalField(max_digits=20, decimal_places=5, default=Decimal("0.00"))
    
    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ['-created_at']