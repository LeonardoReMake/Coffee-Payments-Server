from django.contrib import admin
from .models import Order, Drink, Device, User, Payment, Receipt, Merchant, MerchantCredentials


@admin.register(MerchantCredentials)
class MerchantCredentialsAdmin(admin.ModelAdmin):
    list_display = ('merchant', 'scenario', 'created_at', 'updated_at')
    list_filter = ('scenario', 'created_at')
    search_fields = ('merchant__name', 'scenario')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('device_uuid', 'location', 'status', 'payment_scenario', 'merchant')
    list_filter = ('status', 'payment_scenario')
    search_fields = ('device_uuid', 'location', 'merchant__name')
    readonly_fields = ('uuid', 'last_interaction')
    
    fieldsets = (
        ('Device Information', {
            'fields': ('uuid', 'device_uuid', 'merchant', 'location', 'status', 'last_interaction')
        }),
        ('Payment Configuration', {
            'fields': ('payment_scenario', 'redirect_url')
        }),
        ('Branding', {
            'fields': ('logo_url',)
        }),
        ('Client Information - General', {
            'fields': ('client_info', 'client_error_info'),
            'description': 'General information displayed to customers on order and error screens. Supports HTML formatting.'
        }),
        ('Client Information - Order Status Specific', {
            'fields': (
                'client_info_pending',
                'client_info_paid',
                'client_info_not_paid',
                'client_info_make_pending',
                'client_info_successful',
                'client_info_make_failed'
            ),
            'description': 'Status-specific information displayed to customers on order status tracking page. Supports HTML formatting (e.g., <a href="tel:+1234567890">Call support</a>).'
        }),
    )


admin.site.register(Order)
admin.site.register(Drink)
admin.site.register(User)
admin.site.register(Payment)
admin.site.register(Receipt)
admin.site.register(Merchant)
