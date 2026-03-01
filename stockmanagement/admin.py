# admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import F, ExpressionWrapper, DecimalField
from .models import Stock


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    """
    Premium Professional Admin Configuration for Stock Model
    Optimized for performance, readability, and real-time monitoring
    """

    # =========================
    # LIST VIEW CONFIGURATION
    # =========================
    list_display = (
        "symbol",
        "name",
        "base_asset",
        "quote_asset",
        "colored_current_price",
        "colored_price_change",
        "colored_percentage_change",
        "bid_price",
        "ask_price",
        "last_updated",
    )

    list_display_links = ("symbol", "name")

    list_filter = (
        "base_asset",
        "quote_asset",
        "last_updated",
    )

    search_fields = (
        "symbol",
        "name",
        "base_asset",
        "quote_asset",
    )

    ordering = ("symbol",)

    list_per_page = 50

    date_hierarchy = "last_updated"

    # =========================
    # READONLY FIELDS
    # =========================
    readonly_fields = (
        "last_updated",
        "colored_percentage_change",
        "colored_price_change",
        "daily_range_display",
        "spread_display",
    )

    # =========================
    # FIELDSETS (PREMIUM LAYOUT)
    # =========================
    fieldsets = (

        ("Basic Information", {
            "fields": (
                "symbol",
                "name",
                ("base_asset", "quote_asset"),
            ),
        }),

        ("Price Information", {
            "fields": (
                ("current_price", "open_price"),
                ("high_price", "low_price"),
                ("high_24h", "low_24h"),
            ),
        }),

        ("Market Data", {
            "fields": (
                ("bid_price", "ask_price"),
                "spread_display",
                ("quote_volume_24h",),
            ),
        }),

        ("Change Statistics", {
            "fields": (
                "price_change",
                "colored_price_change",
                "percentage_change",
                "colored_percentage_change",
                "daily_range_display",
            ),
        }),

        ("System Information", {
            "fields": ("last_updated",),
        }),

    )

    # =========================
    # PERFORMANCE OPTIMIZATION
    # =========================
    list_select_related = ()

    # =========================
    # CUSTOM DISPLAY METHODS
    # =========================

    def colored_current_price(self, obj):
        """Premium styled current price"""
        color = "#16a34a" if obj.is_price_positive else "#dc2626"
        return format_html(
            '<strong style="color:{}; font-size:14px;">{}</strong>',
            color,
            obj.current_price
        )
    colored_current_price.short_description = "Last Price"
    colored_current_price.admin_order_field = "current_price"

    def colored_price_change(self, obj):
        """Color coded price change"""
        color = "#16a34a" if obj.price_change >= 0 else "#dc2626"
        sign = "+" if obj.price_change >= 0 else ""
        return format_html(
            '<strong style="color:{};">{}{}</strong>',
            color,
            sign,
            obj.price_change
        )
    colored_price_change.short_description = "Price Change"
    colored_price_change.admin_order_field = "price_change"

    def colored_percentage_change(self, obj):
        """Color coded percentage change"""
        percent = obj.get_change_percentage
        color = "#16a34a" if percent >= 0 else "#dc2626"
        sign = "+" if percent >= 0 else ""

        return format_html(
            '<strong style="color:{};">{}{}%</strong>',
            color,
            sign,
            percent
        )
    colored_percentage_change.short_description = "% Change"

    def daily_range_display(self, obj):
        """Display daily range professionally"""
        return format_html(
            '<span style="font-weight:500;">{}</span>',
            obj.get_daily_range
        )
    daily_range_display.short_description = "Daily Range"

    def spread_display(self, obj):
        """Display bid-ask spread"""
        spread = obj.ask_price - obj.bid_price
        return format_html(
            '<span style="color:#2563eb; font-weight:500;">{}</span>',
            spread
        )
    spread_display.short_description = "Spread"

    # =========================
    # ADMIN HEADER IMPROVEMENTS
    # =========================
    def get_queryset(self, request):
        """Optimized queryset"""
        return super().get_queryset(request)
