from django.contrib import admin
from .models import Order, Drink, Device, User, Payment, Receipt, Merchant, MerchantCredentials


@admin.register(MerchantCredentials)
class MerchantCredentialsAdmin(admin.ModelAdmin):
    list_display = ('merchant', 'scenario', 'created_at', 'updated_at')
    list_filter = ('scenario', 'created_at')
    search_fields = ('merchant__name', 'scenario')
    readonly_fields = ('id', 'created_at', 'updated_at')


admin.site.register(Order)
admin.site.register(Drink)
admin.site.register(Device)
admin.site.register(User)
admin.site.register(Payment)
admin.site.register(Receipt)
admin.site.register(Merchant)
