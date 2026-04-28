from django.contrib import admin
from django.utils.html import format_html
from .models import transaction, payment_settings


@admin.register(transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        'user_display',
        'colored_status',
        'transaction_type',
        'amount',
        'created_at',
        'transaction_id',
        'remark',
    )
    list_filter = ('status', 'transaction_type', 'created_at', 'promo_code')
    search_fields = ('user__username', 'user__email', 'transaction_id', 'remark')
    readonly_fields = ('created_at',)
    list_per_page = 25
    ordering = ('-created_at',)

    fieldsets = (
        ('User & Transaction Info', {
            'fields': ('user', 'transaction_type', 'amount', 'transaction_id', 'remark')
        }),
        ('Promo Code', {
            'fields': ('promo_code', 'promo_code_reward')
        }),
        ('Status & Screenshot', {
            'fields': ('status', 'screenshot')
        }),
        ('System Fields', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def colored_status(self, obj):
        """Display status with color badges."""
        color_map = {
            'PENDING': '#ff9800',
            'REQUESTED': '#2196f3',
            'CANCELLED': '#f44336',
            'COMPLETED': '#4caf50',
            'FAILED': '#9e9e9e',
        }
        color = color_map.get(obj.status, '#000')
        return format_html(
            '<span style="padding:4px 10px; border-radius:10px; color:white; background:{};">{}</span>',
            color, obj.status
        )
    colored_status.short_description = 'Status'

    def user_display(self, obj):
        """Nicely formatted user display."""
        return format_html(
            '<b>{}</b><br><small style="color:#555;">{}</small>',
            obj.user.username, obj.user.email
        )
    user_display.short_description = 'User'


@admin.register(payment_settings)
class PaymentSettingsAdmin(admin.ModelAdmin):
    list_display = ('upi_id', 'preview_qr')
    search_fields = ('upi_id',)

    def preview_qr(self, obj):
        """Show a preview of the UPI QR if integrated later."""
        return format_html(
            '<span style="color:gray;">(Dynamic QR available in payment page)</span>'
        )
    preview_qr.short_description = "QR Preview"

    class Meta:
        verbose_name = "Payment Settings"
        verbose_name_plural = "Payment Settings"
