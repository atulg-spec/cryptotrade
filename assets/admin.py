from django.contrib import admin
from .models import Position, order
from django.utils.html import format_html

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'stock', 'quantity', 'buy_price', 'sell_price',
        'realised_pnl_colored', 'is_closed', 'last_traded_datetime', 'created_at'
    )
    list_filter = ('stock', 'created_at', 'last_traded_datetime')
    search_fields = ('user__username', 'stock__symbol', 'stock__name')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    list_per_page = 20

    fieldsets = (
        ('User & Stock Details', {
            'fields': ('user', 'stock'),
            'classes': ('wide',)
        }),
        ('Trade Information', {
            'fields': ('quantity', 'last_traded_quantity', 'buy_price', 'sell_price', 'last_traded_datetime',),
            'classes': ('wide',)
        }),
        ('Profit / Loss', {
            'fields': ('is_closed', 'realised_pnl',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def realised_pnl_colored(self, obj):
        """Color the PnL for better visualization."""
        color = 'green' if obj.realised_pnl >= 0 else 'red'
        try:
            value = float(obj.realised_pnl)
            return format_html('<b style="color: {};">{:.2f}</b>', color, value)
        except (TypeError, ValueError):
            return format_html('<b style="color: {};">{}</b>', color, obj.realised_pnl)
    realised_pnl_colored.short_description = 'Realised P&L'


@admin.register(order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'stock', 'order_type', 'quantity', 'price', 
        'amount', 'charges', 'status_colored', 'created_at'
    )
    list_filter = ('order_type', 'status', 'created_at', 'stock')
    search_fields = ('user__username', 'stock__symbol', 'stock__name')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    list_per_page = 20
    ordering = ('-created_at',)

    fieldsets = (
        ('Order Details', {
            'fields': ('user', 'stock', 'order_type', 'status'),
            'classes': ('wide',)
        }),
        ('Transaction Information', {
            'fields': ('price', 'quantity', 'amount', 'charges'),
            'classes': ('wide',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def status_colored(self, obj):
        """Color code status for better visibility."""
        color_map = {
            'completed': 'green',
            'pending': 'orange',
            'cancelled': 'gray',
            'failed': 'red',
            'initiated': 'blue',
        }
        color = color_map.get(obj.status, 'black')
        return format_html('<b style="color: {};">{}</b>', color, obj.status.title())
    status_colored.short_description = 'Status'
