import uuid
from django.db import models


class Merchant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    contact_email = models.EmailField()
    bank_account = models.CharField(max_length=255)
    valid_until = models.DateField()  # Новое поле: дата окончания действия услуг
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_active(self):
        """Проверяет, может ли клиент пользоваться сервисом."""
        from django.utils.timezone import now
        return self.valid_until >= now().date()

    def __str__(self):
        return self.name


class Device(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device_uuid = models.CharField(max_length=255, unique=True)  # UUID, задаваемый кофемашиной
    redirect_url = models.URLField(null=True, blank=True)  # Новое поле: URL для перенаправления (необязательное)
    merchant = models.ForeignKey(
        Merchant, on_delete=models.CASCADE, related_name="devices"
    )  # Связь с Merchant
    location = models.CharField(max_length=255)
    status = models.CharField(max_length=50, choices=[
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('error', 'Error')
    ])
    last_interaction = models.DateTimeField()
    payment_scenario = models.CharField(
        max_length=50,
        default='Yookassa',
        help_text='Payment scenario for this device'
    )

    def clean(self):
        from django.conf import settings
        from django.core.exceptions import ValidationError
        
        available_scenarios = getattr(settings, 'PAYMENT_SCENARIOS', ['Yookassa'])
        if self.payment_scenario not in available_scenarios:
            raise ValidationError(
                f'Invalid payment scenario. Must be one of: {", ".join(available_scenarios)}'
            )

    def __str__(self):
        return f"Device {self.device_uuid} ({self.location})"



class Drink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()
    prices = models.JSONField()  # Словарь с ценами в формате {1: 2.50, 2: 3.00, 3: 3.50}
    available = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    external_order_id = models.CharField(max_length=255, null=True, blank=True)  # New field for external order ID
    drink_name = models.CharField(max_length=255)  # Replace ForeignKey with CharField for drink name
    device = models.ForeignKey(
        Device, on_delete=models.CASCADE, related_name="orders"
    )  # Связь с Device
    merchant = models.ForeignKey(
        Merchant, on_delete=models.CASCADE, related_name="orders"
    )  # Связь с Merchant
    size = models.IntegerField(choices=[(1, 'Small'), (2, 'Medium'), (3, 'Large')])
    price = models.DecimalField(max_digits=10, decimal_places=2) # в копейках
    status = models.CharField(max_length=50, choices=[
        ('created', 'Created'),
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('not_paid', 'Not Paid'),
        ('make_pending', 'Make Pending'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
    ])
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self._state.adding and not self.expires_at:
            from django.utils.timezone import now
            from datetime import timedelta
            from django.conf import settings
            
            expiration_minutes = getattr(settings, 'ORDER_EXPIRATION_MINUTES', 15)
            self.expires_at = now() + timedelta(minutes=expiration_minutes)
        
        super().save(*args, **kwargs)

    def is_expired(self):
        """Проверяет, протух ли заказ"""
        from django.utils.timezone import now
        return now() > self.expires_at

    def __str__(self):
        return f"Order {self.id}"


class User(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"User {self.id}"


class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="payments"
    )  # Связь с Order
    merchant = models.ForeignKey(
        Merchant, on_delete=models.CASCADE, related_name="payments"
    )  # Связь с Merchant
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50, choices=[
        ('pending', 'Pending'),
        ('successful', 'Successful'),
        ('failed', 'Failed')
    ])
    transaction_id = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.id}"


class Receipt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="receipts"
    )  # Связь с Order
    contact = models.CharField(max_length=255)
    sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=[
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed')
    ])

    def __str__(self):
        return f"Receipt {self.id}"


class TBankPayment(models.Model):
    order_id = models.CharField(max_length=255, unique=True)
    payment_id = models.CharField(max_length=20, unique=True)
    amount = models.PositiveIntegerField()  # В копейках
    payment_url = models.URLField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=[('new', 'New'), ('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.order_id} - {self.status}"


class MerchantCredentials(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        Merchant,
        on_delete=models.CASCADE,
        related_name='credentials'
    )
    scenario = models.CharField(max_length=50)
    credentials = models.JSONField(
        help_text='Credentials in JSON format. Example for Yookassa: {"account_id": "...", "secret_key": "..."}'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('merchant', 'scenario')
        verbose_name = 'Merchant Credentials'
        verbose_name_plural = 'Merchant Credentials'
    
    def __str__(self):
        return f"{self.merchant.name} - {self.scenario}"
