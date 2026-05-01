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
    # Margin fields (0 = spot/regular trade)
    leverage = models.PositiveSmallIntegerField(default=1)
    is_margin = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ['-created_at']


class Watchlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watchlist')
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'stock')
        verbose_name = "Watchlist Item"
        verbose_name_plural = "Watchlist Items"
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.username} - {self.stock.symbol}"


class MarginPosition(models.Model):
    """
    Tracks a leveraged (margin) position opened by a user.

    How it works (mirrors Binance Cross/Isolated Margin):
      - margin_used  : actual wallet funds locked as collateral
      - leverage     : multiplier (e.g. 10x)
      - position_size: total notional = margin_used * leverage
      - quantity     : contracts/coins held
      - entry_price  : weighted average entry
      - liquidation_price: price at which margin is wiped out
                           Long  : entry * (1 - 1/leverage + maint_margin_ratio)
                           Short : entry * (1 + 1/leverage - maint_margin_ratio)
      - realised_pnl : locked in on partial/full close
    """
    LONG = 'LONG'
    SHORT = 'SHORT'
    SIDE_CHOICES = [(LONG, 'Long'), (SHORT, 'Short')]

    STATUS_OPEN = 'open'
    STATUS_CLOSED = 'closed'
    STATUS_LIQUIDATED = 'liquidated'
    STATUS_CHOICES = [
        (STATUS_OPEN, 'Open'),
        (STATUS_CLOSED, 'Closed'),
        (STATUS_LIQUIDATED, 'Liquidated'),
    ]

    # Maintenance margin rate (same default as Binance tier-1)
    MAINT_MARGIN_RATIO = Decimal('0.004')

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='margin_positions')
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    side = models.CharField(max_length=5, choices=SIDE_CHOICES, default=LONG)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_OPEN)

    leverage = models.PositiveSmallIntegerField(default=10)
    margin_used = models.DecimalField(max_digits=20, decimal_places=5, default=Decimal('0.00'))
    position_size = models.DecimalField(max_digits=20, decimal_places=5, default=Decimal('0.00'))  # notional
    quantity = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal('0'))
    entry_price = models.DecimalField(max_digits=20, decimal_places=5, default=Decimal('0.00'))
    liquidation_price = models.DecimalField(max_digits=20, decimal_places=5, default=Decimal('0.00'))

    realised_pnl = models.DecimalField(max_digits=20, decimal_places=5, default=Decimal('0.00'))
    close_price = models.DecimalField(max_digits=20, decimal_places=5, default=Decimal('0.00'))

    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Margin Position'
        verbose_name_plural = 'Margin Positions'
        ordering = ['-opened_at']

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #
    def _calc_liquidation_price(self):
        """Recalculate liquidation price based on current entry."""
        entry = Decimal(str(self.entry_price))
        lev = Decimal(str(self.leverage))
        mmr = self.MAINT_MARGIN_RATIO
        if self.side == self.LONG:
            return (entry * (1 - 1 / lev + mmr)).quantize(Decimal('0.01'))
        else:
            return (entry * (1 + 1 / lev - mmr)).quantize(Decimal('0.01'))

    def unrealised_pnl(self, current_price):
        """Unrealised P&L for a given market price."""
        current = Decimal(str(current_price))
        qty = Decimal(str(self.quantity))
        entry = Decimal(str(self.entry_price))
        if self.side == self.LONG:
            return (current - entry) * qty
        else:
            return (entry - current) * qty

    def margin_ratio(self, current_price):
        """Current margin ratio — liquidation triggers at ~1.0."""
        upnl = self.unrealised_pnl(current_price)
        margin = Decimal(str(self.margin_used))
        if margin == 0:
            return Decimal('0')
        return ((margin + upnl) / margin).quantize(Decimal('0.0001'))

    def save(self, *args, **kwargs):
        # Always recompute liquidation price on save
        self.liquidation_price = self._calc_liquidation_price()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} {self.side} {self.stock.symbol} x{self.leverage}"