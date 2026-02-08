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
    quantity = models.IntegerField(default=0)
    last_traded_quantity = models.IntegerField(default=0)
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    buy_price = models.FloatField(default=0.0)
    sell_price = models.FloatField(default=0.0)
    realised_pnl = models.FloatField(default=0.0)
    last_traded_datetime = models.DateTimeField(default=timezone.now)
    is_closed = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Position"
        verbose_name_plural = "Positions"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if self.quantity == 0:
            self.is_closed = True
            self.unrealised_pnl = (Decimal(self.sell_price) - Decimal(self.buy_price)) * self.last_traded_quantity
            self.realised_pnl = round((Decimal(self.realised_pnl) + self.unrealised_pnl),2)
            self.unrealised_pnl = 0.0

        self.last_traded_datetime = datetime.datetime.now()
        if self.last_traded_quantity < 0:
            self.last_traded_quantity = self.last_traded_quantity * -1
        self.buy_price = round(self.buy_price, 2)
        self.sell_price = round(self.sell_price, 2)
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
    price = models.FloatField(default=0.0)
    quantity = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=10,choices=order_status,default="pending")
    amount = models.FloatField(default=0.0)
    order_type = models.CharField(choices=order_type,max_length=5,default="")
    charges = models.FloatField(default=0.0)
    
    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ['-created_at']