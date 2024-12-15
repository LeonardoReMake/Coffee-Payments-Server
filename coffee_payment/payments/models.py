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
    drink = models.ForeignKey(
        Drink, on_delete=models.CASCADE, related_name="orders"
    )  # Связь с Drink
    device = models.ForeignKey(
        Device, on_delete=models.CASCADE, related_name="orders"
    )  # Связь с Device
    merchant = models.ForeignKey(
        Merchant, on_delete=models.CASCADE, related_name="orders"
    )  # Связь с Merchant
    size = models.IntegerField(choices=[(1, 'Small'), (2, 'Medium'), (3, 'Large')])
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50, choices=[
        ('created', 'Created'),
        ('paid', 'Paid'),
        ('prepared', 'Prepared'),
        ('failed', 'Failed')
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
