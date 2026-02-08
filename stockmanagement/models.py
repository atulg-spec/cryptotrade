from django.db import models
from decimal import Decimal

class Stock(models.Model):
    """Stock master table"""
    symbol = models.CharField(max_length=15, unique=True, db_index=True)
    name = models.CharField(max_length=150)

    # Price-related fields
    open_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    high_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    low_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    close_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    current_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Additional stock metrics
    volume = models.BigIntegerField(default=0)
    market_cap = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.00'))
    pe_ratio = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    dividend_yield = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))

    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['symbol']

    def __str__(self):
        return f"{self.symbol} - {self.name}"

    @property
    def get_change_percentage(self):
        """Calculate price change percentage from open to current price"""
        if self.open_price and self.open_price > 0:
            change = ((self.current_price - self.open_price) / self.open_price) * 100
            return round(change, 2)
        return 0

    @property
    def is_price_positive(self):
        """Check if price change is positive"""
        return self.get_change_percentage >= 0

    @property
    def get_daily_range(self):
        """Calculate daily price range"""
        return self.high_price - self.low_price