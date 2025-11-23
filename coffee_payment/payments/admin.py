from django.contrib import admin
from .models import Order, Drink, Device, User, Payment, Receipt, Merchant, MerchantCredentials


@admin.register(MerchantCredentials)
class MerchantCredentialsAdmin(admin.ModelAdmin):
    list_display = ('merchant', 'scenario', 'status_check_type', 'created_at', 'updated_at')
    list_filter = ('scenario', 'status_check_type', 'created_at')
    search_fields = ('merchant__name', 'scenario')
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Merchant Information', {
            'fields': ('merchant', 'scenario')
        }),
        ('Credentials', {
            'fields': ('credentials',),
            'description': 'Credentials in JSON format. Example for Yookassa: {"account_id": "...", "secret_key": "..."}'
        }),
        ('Payment Status Check Configuration', {
            'fields': ('status_check_type',),
            'description': 'Type of payment status check: polling (background check), webhook (notification from payment provider), or none (no automatic check)'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('device_uuid', 'location', 'status', 'payment_scenario', 'merchant')
    list_filter = ('status', 'payment_scenario')
    search_fields = ('device_uuid', 'location', 'merchant__name')
    readonly_fields = ('uuid',)
    
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
                'client_info_make_failed',
                'client_info_manual_make'
            ),
            'description': 'Status-specific information displayed to customers on order status tracking page. Supports HTML formatting (e.g., <a href="tel:+1234567890">Call support</a>).'
        }),
    )


@admin.register(Drink)
class DrinkAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'available')
    list_filter = ('available',)
    search_fields = ('name', 'description')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'description', 'available')
        }),
        ('Pricing', {
            'fields': ('prices',),
            'description': 'Price mapping by size in format: {1: 2.50, 2: 3.00, 3: 3.50}'
        }),
        ('Receipt Metadata', {
            'fields': ('meta',),
            'description': 'Receipt metadata for YookassaReceipt scenario. Example: {"vat_code": 2, "measure": "piece", "payment_subject": "commodity", "payment_mode": "full_payment"}'
        }),
    )


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'contact', 'amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('contact', 'order__id', 'drink_no')
    readonly_fields = ('id', 'created_at', 'sent_at')
    
    fieldsets = (
        ('Receipt Information', {
            'fields': ('id', 'order', 'contact', 'drink_no', 'amount', 'status')
        }),
        ('Receipt Data', {
            'fields': ('receipt_data',),
            'description': 'Complete receipt data sent to Yookassa in JSON format'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'sent_at')
        }),
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'drink_name', 'status', 'status_check_type', 'price', 'created_at')
    list_filter = ('status', 'status_check_type', 'created_at')
    search_fields = ('id', 'drink_name', 'device__device_uuid', 'merchant__name')
    readonly_fields = ('id', 'status_check_type', 'payment_reference_id', 'created_at', 'updated_at', 'expires_at', 'payment_started_at', 'next_check_at', 'last_check_at', 'check_attempts')
    
    fieldsets = (
        ('Order Information', {
            'fields': ('id', 'device', 'merchant', 'drink_name', 'drink_number', 'size', 'price', 'status')
        }),
        ('Payment Information', {
            'fields': ('payment_reference_id', 'status_check_type'),
            'description': 'status_check_type is fixed at payment initiation time and cannot be changed'
        }),
        ('Background Check Tracking', {
            'fields': ('payment_started_at', 'next_check_at', 'last_check_at', 'check_attempts', 'failed_presentation_desc'),
            'description': 'Fields used for background payment status checking'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'expires_at')
        }),
    )


admin.site.register(User)
admin.site.register(Payment)
admin.site.register(Merchant)
