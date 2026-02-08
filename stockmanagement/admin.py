from django.contrib import admin
from django.utils.html import format_html
from .models import Stock
from decimal import Decimal, InvalidOperation


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    """Elegant Django admin for Stock with safe formatting and visuals."""

    list_display = (
        'symbol', 'name',
        'formatted_current_price', 'formatted_open_price',
        'formatted_high_price', 'formatted_low_price',
        'price_change_colored', 'formatted_market_cap',
        'formatted_pe_ratio', 'formatted_dividend_yield',
        'formatted_volume', 'last_updated'
    )
    list_display_links = ('symbol', 'name')
    search_fields = ('symbol', 'name')
    list_filter = ('last_updated',)
    ordering = ('symbol',)
    readonly_fields = ("last_updated",)

    fieldsets = (
        ("Basic Info", {"fields": ("symbol", "name")}),
        ("Price Details", {
            "fields": (
                "open_price", "high_price", "low_price",
                "close_price", "current_price"
            )
        }),
        ("Stock Metrics", {
            "fields": (
                "volume", "market_cap", "pe_ratio", "dividend_yield"
            )
        }),
        ("System Info", {"fields": ("last_updated",)}),
    )

    # =============== SAFE HELPER ===============

    def as_decimal(self, value):
        """Safely convert a value to Decimal, returning 0.00 if invalid."""
        try:
            if isinstance(value, (float, int, Decimal)):
                return Decimal(str(value))
            return Decimal(str(value).replace(',', ''))
        except (InvalidOperation, TypeError, ValueError):
            return Decimal('0.00')

    # =============== FORMATTED DISPLAY FIELDS ===============

    def formatted_current_price(self, obj):
        value = self.as_decimal(obj.current_price)
        return format_html(f'<b style="color:#22c55e;">₹{value}</b>')
    formatted_current_price.short_description = "Current Price"

    def formatted_open_price(self, obj):
        value = self.as_decimal(obj.open_price)
        return f"₹{value:,.2f}"
    formatted_open_price.short_description = "Open"

    def formatted_high_price(self, obj):
        value = self.as_decimal(obj.high_price)
        return f"₹{value:,.2f}"
    formatted_high_price.short_description = "High"

    def formatted_low_price(self, obj):
        value = self.as_decimal(obj.low_price)
        return f"₹{value:,.2f}"
    formatted_low_price.short_description = "Low"

    def formatted_market_cap(self, obj):
        value = self.as_decimal(obj.market_cap)
        return f"₹{value:,.2f}"
    formatted_market_cap.short_description = "Market Cap"

    def formatted_volume(self, obj):
        try:
            return f"{int(obj.volume):,}"
        except (ValueError, TypeError):
            return "—"
    formatted_volume.short_description = "Volume"

    def formatted_pe_ratio(self, obj):
        value = self.as_decimal(obj.pe_ratio)
        return f"{value:.2f}"
    formatted_pe_ratio.short_description = "P/E"

    def formatted_dividend_yield(self, obj):
        value = self.as_decimal(obj.dividend_yield)
        return f"{value:.2f}%"
    formatted_dividend_yield.short_description = "Dividend Yield"

    def price_change_colored(self, obj):
        """Show colored percentage change (green/red)."""
        change = obj.get_change_percentage or Decimal('0.00')
        color = "#22c55e" if change > 0 else "#ef4444"
        arrow = "▲" if change > 0 else "▼"
        return format_html(
            f'<span style="color:{color}; font-weight:600;">{arrow} {change}%</span>'
        )
    price_change_colored.short_description = "Change (%)"

    class Media:
        css = {
            'all': (
                'https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css',
            )
        }
