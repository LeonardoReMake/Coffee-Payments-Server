# Design Document

## Overview

Данный документ описывает проектное решение для добавления функциональности конфигурации сценариев оплаты в системе Coffee Payments Server. Решение позволит каждой кофемашине (Device) использовать различные сценарии оплаты (Yookassa, TBank, Custom), а каждому мерчанту хранить свои учетные данные (Credentials) для каждого сценария.

Основные цели:
- Обеспечить гибкость в выборе платежных провайдеров для каждой кофемашины
- Централизованно хранить учетные данные мерчантов для различных сценариев
- Поддержать интеграцию с внешними системами оплаты через сценарий Custom
- Минимизировать изменения в существующем коде (MVP подход)

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Django Settings                          │
│  PAYMENT_SCENARIOS = ['Yookassa', 'TBank', 'Custom']        │
│  DEFAULT_PAYMENT_SCENARIO = 'Yookassa'                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Database Models                         │
│                                                              │
│  ┌──────────────┐      ┌──────────────────────────┐        │
│  │   Device     │      │  MerchantCredentials     │        │
│  ├──────────────┤      ├──────────────────────────┤        │
│  │ + scenario   │      │ + merchant (FK)          │        │
│  │   (CharField)│      │ + scenario (CharField)   │        │
│  └──────────────┘      │ + credentials (JSONField)│        │
│                        └──────────────────────────┘        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Payment Processing Flow                    │
│                                                              │
│  1. Validate Device & Merchant                              │
│  2. Get Device.scenario                                     │
│  3. Get MerchantCredentials for (merchant, scenario)        │
│  4. Create Order (status='created')                         │
│  5. Execute Scenario:                                       │
│     - Yookassa: create_payment() with credentials           │
│     - TBank: create_payment() with credentials              │
│     - Custom: redirect to Device.redirect_url               │
└─────────────────────────────────────────────────────────────┘
```

### Payment Scenario Flow

```
User scans QR → qr_code_redirect() → Validate Device/Merchant
                                              │
                                              ▼
                                    Get Device.scenario
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │                         │                         │
                    ▼                         ▼                         ▼
              [Yookassa]                  [TBank]                  [Custom]
                    │                         │                         │
                    ▼                         ▼                         ▼
        Get Yookassa Credentials   Get TBank Credentials    Validate redirect_url
                    │                         │                         │
                    ▼                         ▼                         ▼
        Create Order (created)     Create Order (created)   Create Order (created)
                    │                         │                         │
                    ▼                         ▼                         ▼
        yookassa_service.          tbank_service.           Redirect to
        create_payment()           create_payment()         Device.redirect_url
                    │                         │                         │
                    ▼                         ▼                         ▼
        Update Order (pending)     Update Order (pending)   External system
                    │                         │              handles payment
                    ▼                         ▼
        Redirect to payment        Redirect to payment
```

## Components and Interfaces

### 1. Database Models

#### 1.1 Device Model (Modified)

Добавляется новое поле `payment_scenario` для хранения выбранного сценария оплаты.

```python
class Device(models.Model):
    # ... existing fields ...
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
```

#### 1.2 MerchantCredentials Model (New)

Новая модель для хранения учетных данных мерчантов для различных сценариев.

```python
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
```

### 2. Settings Configuration

Добавление новых настроек в `settings.py`:

```python
# Payment scenarios configuration
PAYMENT_SCENARIOS = ['Yookassa', 'TBank', 'Custom']
DEFAULT_PAYMENT_SCENARIO = 'Yookassa'
```

### 3. Service Layer

#### 3.1 Payment Scenario Service (New)

Новый сервис для управления логикой выбора и выполнения сценариев оплаты.

```python
# payments/services/payment_scenario_service.py

class PaymentScenarioService:
    
    @staticmethod
    def get_merchant_credentials(merchant, scenario):
        """
        Получает учетные данные мерчанта для указанного сценария.
        Raises: ValueError if credentials not found
        """
        pass
    
    @staticmethod
    def execute_scenario(device, order, drink_details):
        """
        Выполняет сценарий оплаты для устройства.
        Returns: HttpResponse (redirect or error)
        """
        pass
    
    @staticmethod
    def execute_yookassa_scenario(device, order, drink_details, credentials):
        """Выполняет сценарий Yookassa"""
        pass
    
    @staticmethod
    def execute_tbank_scenario(device, order, drink_details, credentials):
        """Выполняет сценарий TBank"""
        pass
    
    @staticmethod
    def execute_custom_scenario(device, order):
        """Выполняет сценарий Custom"""
        pass
```

#### 3.2 Modified Yookassa Service

Модификация существующего сервиса для использования динамических credentials:

```python
# payments/services/yookassa_service.py

def create_payment(amount, description, return_url, drink_no, order_uuid, size, credentials):
    """
    Creates payment using provided credentials instead of hardcoded ones.
    
    Args:
        credentials: dict with 'account_id' and 'secret_key'
    """
    from yookassa import Configuration, Payment
    
    # Configure with merchant-specific credentials
    Configuration.account_id = credentials['account_id']
    Configuration.secret_key = credentials['secret_key']
    
    # ... rest of the payment creation logic
```

#### 3.3 Modified TBank Service

Модификация существующего сервиса для использования динамических credentials:

```python
# payments/services/t_bank_service.py

def create_payment_api(data, credentials):
    """
    Creates payment using provided credentials.
    
    Args:
        credentials: dict with TBank-specific fields
    """
    # Use credentials from parameter instead of settings
```

### 4. View Layer

#### 4.1 Modified yookassa_payment_process View

Основные изменения в существующем view для поддержки сценариев:

```python
@csrf_exempt
def yookassa_payment_process(request):
    # ... existing validation logic ...
    
    device = get_object_or_404(Device, device_uuid=device_uuid)
    merchant = device.merchant
    
    # Create order with 'created' status first
    order = Order.objects.create(
        drink_name=drink_name,
        device=device,
        merchant=merchant,
        size=drink_size_int,
        price=drink_price,
        status='created'
    )
    log_info(f"Order {order.id} created with status 'created'", 'yookassa_payment_process')
    
    # Execute payment scenario
    try:
        from payments.services.payment_scenario_service import PaymentScenarioService
        return PaymentScenarioService.execute_scenario(device, order, drink_details)
    except ValueError as e:
        order.status = 'failed'
        order.save()
        log_error(f"Failed to execute payment scenario: {str(e)}", 'yookassa_payment_process', 'ERROR')
        return render_error_page(str(e), 400)
    except Exception as e:
        order.status = 'failed'
        order.save()
        log_error(f"Failed to process payment: {str(e)}", 'yookassa_payment_process', 'ERROR')
        return render_error_page('Service temporarily unavailable', 503)
```

## Data Models

### MerchantCredentials JSON Structure

Структура JSON для различных сценариев:

#### Yookassa Credentials
```json
{
  "account_id": "1193510",
  "secret_key": "test_Ku1e9ZkX5OoTCm0k2m05Dg66XldJFHkER_9sw5LKE1E"
}
```

#### TBank Credentials
```json
{
  "shop_id": "ShopID123",
  "secret_key": "SecretKey456",
  "success_url": "https://example.com/success",
  "fail_url": "https://example.com/fail"
}
```

#### Custom Credentials
```json
{
  "api_key": "custom_api_key",
  "additional_param": "value"
}
```

### Database Schema Changes

#### Migration 1: Add payment_scenario to Device

```python
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('payments', '0009_order_expires_at_alter_order_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='payment_scenario',
            field=models.CharField(default='Yookassa', max_length=50),
        ),
    ]
```

#### Migration 2: Create MerchantCredentials model

```python
from django.db import migrations, models
import django.db.models.deletion
import uuid

class Migration(migrations.Migration):
    dependencies = [
        ('payments', '0010_device_payment_scenario'),
    ]

    operations = [
        migrations.CreateModel(
            name='MerchantCredentials',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('scenario', models.CharField(max_length=50)),
                ('credentials', models.JSONField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('merchant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='credentials', to='payments.merchant')),
            ],
            options={
                'verbose_name': 'Merchant Credentials',
                'verbose_name_plural': 'Merchant Credentials',
                'unique_together': {('merchant', 'scenario')},
            },
        ),
    ]
```

## Error Handling

### Error Scenarios and Responses

1. **Missing Credentials**
   - Condition: MerchantCredentials not found for (merchant, scenario)
   - Action: Set Order.status = 'failed', log error
   - Response: HTTP 400 with message "Payment credentials not configured for this merchant"

2. **Invalid Payment Scenario**
   - Condition: Device.payment_scenario not in PAYMENT_SCENARIOS
   - Action: Validation error during Device save
   - Response: ValidationError

3. **Missing redirect_url for Custom Scenario**
   - Condition: Device.payment_scenario = 'Custom' and Device.redirect_url is None/empty
   - Action: Set Order.status = 'failed', log error
   - Response: HTTP 400 with message "Redirect URL not configured for custom payment scenario"

4. **Payment Provider API Failure**
   - Condition: Yookassa/TBank API returns error
   - Action: Set Order.status = 'failed', log error with full request details
   - Response: HTTP 503 with message "Service temporarily unavailable"

### Logging Strategy

Все операции должны логироваться с использованием существующего логгера:

```python
# При выборе сценария
log_info(f"Device {device.device_uuid} using payment scenario: {device.payment_scenario}", 'payment_scenario_service')

# При получении credentials
log_info(f"Retrieved credentials for Merchant {merchant.id}, scenario: {scenario}", 'payment_scenario_service')

# При выполнении платежа
log_info(f"Processing payment for Order {order.id} using scenario {device.payment_scenario}. Request params: ...", 'payment_scenario_service')

# При ошибке
log_error(f"Failed to process payment for Order {order.id}: {error_message}. Scenario: {device.payment_scenario}, Merchant: {merchant.id}", 'payment_scenario_service', 'ERROR')
```

## Testing Strategy

### Unit Tests

1. **Model Tests**
   - Test Device.payment_scenario validation
   - Test MerchantCredentials unique constraint
   - Test MerchantCredentials JSON field storage

2. **Service Tests**
   - Test PaymentScenarioService.get_merchant_credentials()
     - Success case
     - Missing credentials case
   - Test PaymentScenarioService.execute_scenario()
     - For each scenario type
     - Error handling

3. **Integration Tests**
   - Test full payment flow for Yookassa scenario
   - Test full payment flow for TBank scenario
   - Test full payment flow for Custom scenario
   - Test error cases (missing credentials, invalid scenario)

### Test Data Setup

```python
# Test fixtures
merchant = Merchant.objects.create(
    name='Test Merchant',
    contact_email='test@example.com',
    bank_account='123456',
    valid_until=date.today() + timedelta(days=365)
)

# Yookassa credentials
MerchantCredentials.objects.create(
    merchant=merchant,
    scenario='Yookassa',
    credentials={
        'account_id': 'test_account',
        'secret_key': 'test_secret'
    }
)

# Device with Yookassa scenario
device = Device.objects.create(
    device_uuid='test-device-001',
    merchant=merchant,
    location='Test Location',
    status='online',
    last_interaction=timezone.now(),
    payment_scenario='Yookassa'
)
```

### Manual Testing Checklist

1. Create Merchant with credentials for each scenario
2. Create Device with each scenario type
3. Test QR code scan → payment flow for each scenario
4. Test error cases:
   - Device without credentials
   - Custom scenario without redirect_url
   - Invalid scenario name
5. Verify logging output for all operations
6. Test Django Admin interface for managing credentials

## Implementation Notes

### MVP Approach

Следуя принципу MVP из CONSTITUTION.md:

1. **Минимальные изменения в существующем коде**
   - Модификация только необходимых views
   - Использование существующих сервисов где возможно

2. **Простое хранение credentials**
   - JSON поле без дополнительной структуры
   - Без шифрования на первом этапе (можно добавить позже)

3. **Базовая валидация**
   - Проверка существования credentials
   - Проверка наличия redirect_url для Custom
   - Без сложной валидации структуры JSON

4. **Использование существующих библиотек**
   - Django ORM для работы с БД
   - Существующие yookassa и requests библиотеки

### Future Enhancements (Out of Scope for MVP)

- Шифрование credentials в БД
- Валидация структуры JSON credentials для каждого сценария
- UI для управления credentials
- Поддержка дополнительных сценариев оплаты
- Webhook обработка для Custom сценария
- Ротация credentials
- Audit log для изменений credentials

## Security Considerations

1. **Credentials Storage**
   - Credentials хранятся в БД в открытом виде (MVP)
   - Доступ к БД должен быть ограничен
   - В будущем рекомендуется добавить шифрование

2. **Admin Access**
   - Только администраторы должны иметь доступ к MerchantCredentials в Django Admin
   - Рекомендуется настроить permissions

3. **Logging**
   - Не логировать полные credentials
   - Логировать только идентификаторы (merchant_id, scenario)

4. **Validation**
   - Валидация payment_scenario при сохранении Device
   - Проверка существования credentials перед обработкой платежа
