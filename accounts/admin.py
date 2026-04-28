from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser
from django.contrib.auth.forms import UserChangeForm
# from paper_admin.admin.widgets import AdminCheckboxTree

# class CustomUserChangeForm(UserChangeForm):
#     class Meta:
#         widgets = {
#             "user_permissions": AdminCheckboxTree,
#         }


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('username', 'phone_number', 'first_name','email', 'is_staff', 'wallet', 'is_active', 'date_joined')
    list_filter = ('is_staff', 'is_active', 'city', 'region_name')
    search_fields = ('username', 'phone_number', 'email')
    ordering = ('-date_joined',)
    readonly_fields = ('date_joined', 'last_login')  # Mark date_joined as read-only

    fieldsets = (
        (None, {'fields': ('username', 'email', 'phone_number', 'password')}),
        (('Personal Info'), {'fields': ('first_name', 'last_name', 'region_name', 'city', 'zip_code', 'lat', 'lon', 'timezone', 'isp')}),
        (('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (('Wallet Information'), {'fields': ('wallet',)}),
        (('Account Information'), {'fields': ('bank_account_name', 'bank_account_number', 'upi_id', 'ifsc_code')}),
        (('Important Dates'), {'fields': ('last_login', 'date_joined')}),  # Add read-only fields here
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'phone_number', 'email', 'password1', 'password2', 'is_staff', 'is_active'),
        }),
    )
    # form = CustomUserChangeForm
