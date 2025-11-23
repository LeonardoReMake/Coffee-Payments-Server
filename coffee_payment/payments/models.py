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
        ('error', 'Error'),
        ('test', 'Test')
    ])
    last_interaction = models.DateTimeField()
    payment_scenario = models.CharField(
        max_length=50,
        default='Yookassa',
        help_text='Payment scenario for this device'
    )
    logo_url = models.URLField(
        null=True,
        blank=True,
        help_text='URL to merchant logo image displayed on order screen'
    )
    client_info = models.TextField(
        null=True,
        blank=True,
        help_text='Custom information displayed to customers on order screen'
    )
    client_error_info = models.TextField(
        null=True,
        blank=True,
        help_text='Custom information displayed to customers on error screens. Supports HTML formatting (e.g., <a href="tel:+1234567890">Call support</a>)'
    )
    client_info_pending = models.TextField(
        null=True,
        blank=True,
        help_text='Information displayed to customers when order status is pending. Supports HTML formatting.'
    )
    client_info_paid = models.TextField(
        null=True,
        blank=True,
        help_text='Information displayed to customers when order status is paid. Supports HTML formatting.'
    )
    client_info_not_paid = models.TextField(
        null=True,
        blank=True,
        help_text='Information displayed to customers when order status is not_paid. Supports HTML formatting.'
    )
    client_info_make_pending = models.TextField(
        null=True,
        blank=True,
        help_text='Information displayed to customers when order status is make_pending. Supports HTML formatting.'
    )
    client_info_successful = models.TextField(
        null=True,
        blank=True,
        help_text='Information displayed to customers when order status is successful. Supports HTML formatting.'
    )
    client_info_make_failed = models.TextField(
        null=True,
        blank=True,
        help_text='Information displayed to customers when order status is make_failed. Supports HTML formatting.'
    )
    client_info_manual_make = models.TextField(
        null=True,
        blank=True,
        help_text='Information displayed to customers when order status is manual_make. Supports HTML formatting.'
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
    id = models.CharField(primary_key=True, max_length=255)  # Changed from UUID to string for device compatibility
    name = models.CharField(max_length=255)
    description = models.TextField()
    prices = models.JSONField()  # Словарь с ценами в формате {1: 2.50, 2: 3.00, 3: 3.50}
    available = models.BooleanField(default=True)
    meta = models.JSONField(
        null=True,
        blank=True,
        help_text='Receipt metadata in JSON format. Example: {"vat_code": 2, "measure": "piece", "payment_subject": "commodity", "payment_mode": "full_payment"}'
    )

    def __str__(self):
        return self.name


class Order(models.Model):
    """
    Order model representing a coffee order.
    
    The id field accepts machine-generated order IDs from coffee machines
    in custom formats (e.g., '20250317110122659ba6d7-9ace-cndn').
    These IDs are provided via QR code parameters and serve as the primary
    identifier for the order throughout the payment flow.
    """
    id = models.CharField(primary_key=True, max_length=255)
    payment_reference_id = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        help_text='Payment system reference ID (e.g., Yookassa payment_id)'
    )
    drink_name = models.CharField(max_length=255)  # Replace ForeignKey with CharField for drink name
    drink_number = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Drink ID at the device (drinkNo from QR code)'
    )
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
        ('manual_make', 'Manual Make'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
        ('make_failed', 'Make Failed'),
    ])
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Background payment check fields
    payment_started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp when user was redirected to payment provider (with timezone)'
    )
    next_check_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp for next payment status check (with timezone)'
    )
    last_check_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp of last payment status check (with timezone)'
    )
    check_attempts = models.IntegerField(
        default=0,
        help_text='Number of payment status check attempts'
    )
    failed_presentation_desc = models.TextField(
        null=True,
        blank=True,
        help_text='User-friendly description of failure reason'
    )
    
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
    contact = models.CharField(max_length=255)  # Email address
    drink_no = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Drink ID at the device'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Payment amount in kopecks'
    )
    receipt_data = models.JSONField(
        null=True,
        blank=True,
        help_text='Complete receipt data sent to Yookassa in JSON format'
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=[
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed')
    ])
    created_at = models.DateTimeField(auto_now_add=True)

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
