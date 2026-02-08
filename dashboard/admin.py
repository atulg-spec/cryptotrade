# admin_panel/admin.py
from django.contrib import admin
from django.contrib.auth.models import Group

# Unregister default Group
admin.site.unregister(Group)

from django.contrib import admin
from django.utils.html import format_html
from .models import SiteSettings, PromoCode


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = (
        'site_name',
        'tagline',
        'contact_email',
        'contact_phone',
        'updated_at',
        'logo_preview',
        'icon_preview',
    )
    readonly_fields = ('created_at', 'updated_at', 'logo_preview', 'icon_preview')
    search_fields = ('site_name', 'tagline', 'contact_email')
    list_filter = ('updated_at', 'created_at')
    ordering = ('-updated_at',)

    fieldsets = (
        ('🏠 Basic Information', {
            'fields': ('site_name', 'tagline')
        }),
        ('🖼️ Branding', {
            'fields': ('logo', 'logo_preview', 'icon', 'icon_preview'),
            'description': "Upload your website logo and favicon for consistent branding."
        }),
        ('📞 Contact Details', {
            'fields': ('contact_email', 'contact_phone', 'contact_url'),
        }),
        ('🌐 Social Media Links', {
            'fields': ('facebook', 'twitter', 'instagram', 'linkedin', 'youtube'),
            'description': "Add links to your social media profiles."
        }),
        ('⏱️ Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )

    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="width:60px; height:auto; border-radius:6px; box-shadow:0 2px 6px rgba(0,0,0,0.15);" />',
                obj.logo.url
            )
        return "No logo"

    logo_preview.short_description = "Logo Preview"

    def icon_preview(self, obj):
        if obj.icon:
            return format_html(
                '<img src="{}" style="width:32px; height:32px; border-radius:4px; box-shadow:0 1px 4px rgba(0,0,0,0.2);" />',
                obj.icon.url
            )
        return "No icon"

    icon_preview.short_description = "Icon Preview"

    class Media:
        css = {
            'all': (
                'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css',
                'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap',
            )
        }
        js = ()


# Optional — for sites that only need one settings object
# This ensures only one SiteSettings instance can be created.
    def has_add_permission(self, request):
        """Restrict addition to only one instance."""
        if SiteSettings.objects.exists():
            return False
        return True

from django.contrib import admin
from .models import PromoCode


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    # Columns visible in admin list view
    list_display = (
        "promo_code",
        "promo_type",
        "reward_value",
        "created_at",
    )

    # Add filters on sidebar
    list_filter = ("promo_type", "created_at")

    # Enable searching
    search_fields = ("promo_code",)

    # Read-only fields
    readonly_fields = ("created_at",)

    # Nicely group fields in admin form
    fieldsets = (
        ("Promo Code Details", {
            "fields": ("promo_code", "promo_type")
        }),
        ("Reward Settings", {
            "fields": ("reward_amount", "reward_percentage"),
            "description": "Fill only the field required for selected promo type."
        }),
        ("System Info", {
            "classes": ("collapse",),
            "fields": ("created_at",)
        }),
    )

    # Custom validation inside admin panel
    def save_model(self, request, obj, form, change):
        if obj.promo_type == "amount" and not obj.reward_amount:
            raise admin.ValidationError("Reward amount is required for 'amount' promo type.")
        if obj.promo_type == "percentage" and not obj.reward_percentage:
            raise admin.ValidationError("Reward percentage is required for 'percentage' promo type.")
        super().save_model(request, obj, form, change)

    # Custom method to show amount/percentage cleanly
    def reward_value(self, obj):
        if obj.promo_type == "amount":
            return f"₹{obj.reward_amount}"
        return f"{obj.reward_percentage}%"
    
    reward_value.short_description = "Reward Value"


# Customize admin site
admin.site.site_header = "Administration"
admin.site.site_title = "Admin Panel"
admin.site.index_title = "Welcome to Admin Panel"