from django.contrib import admin
from .models import Order, Drink, Device, User, Payment, Receipt, Merchant

admin.site.register(Order)
admin.site.register(Drink)
admin.site.register(Device)
admin.site.register(User)
admin.site.register(Payment)
admin.site.register(Receipt)
admin.site.register(Merchant)
