# Design Document

## Overview

This document describes the design for implementing the YookassaReceipt payment scenario, which extends the existing Yookassa scenario with fiscal receipt generation capabilities. The implementation follows MVP principles, reusing existing infrastructure while adding minimal new components for receipt handling.

## Architecture

### High-Level Design

The YookassaReceipt scenario extends the existing Yookassa payment flow by:
1. Adding email collection on the order status page (for status=created)
2. Modifying the Drink model to store receipt metadata
3. Extending the payment creation logic to include receipt data
4. Persisting receipt information in the Receipt model

```
┌─────────────────────────────────────────────────────────────┐
│                    Payment Flow                              │
│                                                              │
│  QR Scan → process_payment_flow() → Order (created)         │
│                                                              │
│  ↓                                                           │
│                                                              │
│  Order Status Page (YookassaReceipt scenario)               │
│  - Display order info                                       │
│  - Show email input field                                   │
│  - Validate email (optional/mandatory based on config)      │
│                                                              │
│  ↓ (User clicks "Перейти к оплате")                        │
│                                                              │
│  initiate_payment() → YookassaReceiptService                │
│  - Get merchant credentials (YookassaReceipt)               │
│  - Build receipt object with fallback logic                 │
│  - Create Yookassa payment with receipt                     │
│  - Save Receipt record                                      │
│                                                              │
│  ↓                                                           │
│                                                              │
│  Yookassa Payment Page → Webhook → Order (paid)             │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Database Models

#### 1.1 Drink Model Changes

**Current State:**
```python
class Drink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()
    prices = models.JSONField()
    available = models.BooleanField(default=True)
```

**New Design:**
```python
class Drink(models.Model):
    id = models.IntegerField(primary_key=True)  # Changed from UUID to integer
    name = models.CharField(max_length=255)
    description = models.TextField()
    prices = models.JSONField()
    available = models.BooleanField(default=True)
    meta = models.JSONField(
        null=True,
        blank=True,
        help_text='Receipt metadata in JSON format. Example: {"vat_code": 2, "measure": "piece", "payment_subject": "commodity", "payment_mode": "full_payment"}'
    )
```

**Migration Strategy:**
- Create migration to change id field from UUID to Integer
- Existing Drink records will need to be migrated (manual data migration if needed)
- Add meta field as nullable JSON field

#### 1.2 Receipt Model Enhancement

**Current State:**
```python
class Receipt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="receipts")
    contact = models.CharField(max_length=255)
    sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=[...])
```

**New Design:**
```python
class Receipt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="receipts")
    contact = models.CharField(max_length=255)  # Email address
    drink_no = models.CharField(max_length=255, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
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
```

**Changes:**
- Add drink_no field to store drink identifier
- Add amount field to store payment amount
- Add receipt_data field to store complete receipt JSON
- Add created_at field for audit trail

### 2. Service Layer

#### 2.1 YookassaReceiptService

**Location:** `coffee_payment/payments/services/yookassa_receipt_service.py`

**Purpose:** Extends Yookassa payment creation with receipt generation logic

**Interface:**
```python
class YookassaReceiptService:
    """
    Service for creating Yookassa payments with fiscal receipts.
    Extends base Yookassa functionality with receipt generation.
    """
    
    @staticmethod
    def create_payment_with_receipt(
        amount: float,
        description: str,
        return_url: str,
        drink_no: str,
        order_uuid: str,
        size: str,
        credentials: dict,
        email: str = None,
        drink_meta: dict = None
    ) -> Payment:
        """
        Creates a Yookassa payment with optional receipt.
        
        Args:
            amount: Payment amount in rubles
            description: Payment description
            return_url: URL to redirect after payment
            drink_no: Drink number/ID
            order_uuid: Order UUID
            size: Drink size
            credentials: Merchant credentials including receipt settings
            email: Customer email (optional)
            drink_meta: Drink metadata for receipt (optional)
            
        Returns:
            Payment object from Yookassa API
        """
        pass
    
    @staticmethod
    def build_receipt_object(
        email: str,
        drink_name: str,
        amount: float,
        credentials: dict,
        drink_meta: dict = None
    ) -> dict:
        """
        Builds receipt object for Yookassa API.
        
        Implements fallback logic:
        1. Try to get field from drink_meta
        2. If not found, try to get from credentials
        3. If not found in either, exclude field
        
        Args:
            email: Customer email
            drink_name: Name of the drink
            amount: Payment amount in rubles
            credentials: Merchant credentials
            drink_meta: Drink metadata (optional)
            
        Returns:
            dict: Receipt object for Yookassa API
        """
        pass
    
    @staticmethod
    def save_receipt_record(
        order: Order,
        email: str,
        receipt_data: dict
    ) -> Receipt:
        """
        Saves receipt record to database.
        
        Args:
            order: Order instance
            email: Customer email
            receipt_data: Complete receipt data sent to Yookassa
            
        Returns:
            Receipt: Created receipt instance
        """
        pass
```

**Implementation Details:**

1. **Receipt Object Construction:**
   - Customer email is required
   - Item fields (vat_code, measure, payment_subject, payment_mode) use fallback logic
   - Receipt-level fields (tax_system_code, timezone) come from credentials
   - Fields not found in either source are excluded

2. **Fallback Logic:**
   ```python
   def get_field_with_fallback(field_name, drink_meta, credentials):
       if drink_meta and field_name in drink_meta:
           return drink_meta[field_name]
       if field_name in credentials:
           return credentials[field_name]
       return None
   ```

3. **Receipt Object Format:**
   ```json
   {
       "customer": {
           "email": "customer@example.com"
       },
       "items": [
           {
               "description": "Американо",
               "amount": {
                   "value": "150.00",
                   "currency": "RUB"
               },
               "vat_code": 2,
               "quantity": 1,
               "measure": "piece",
               "payment_subject": "commodity",
               "payment_mode": "full_payment"
           }
       ],
       "internet": false,
       "tax_system_code": 1,
       "timezone": 1
   }
   ```

#### 2.2 PaymentScenarioService Extension

**Changes to existing service:**

Add new scenario handler:
```python
@staticmethod
def execute_yookassa_receipt_scenario(device, order, drink_details, email=None):
    """
    Executes YookassaReceipt payment scenario.
    
    Args:
        device: Device instance
        order: Order instance with status='created'
        drink_details: Dict containing drink information
        email: Customer email for receipt (optional)
        
    Returns:
        HttpResponseRedirect: Redirect to Yookassa payment page
        
    Raises:
        ValueError: If YookassaReceipt credentials are missing
    """
    pass
```

Update execute_scenario method to handle YookassaReceipt:
```python
if scenario == 'YookassaReceipt':
    return PaymentScenarioService.execute_yookassa_receipt_scenario(
        device, order, drink_details, email=request_email
    )
```

### 3. View Layer

#### 3.1 Order Status Page Modifications

**Template:** `coffee_payment/templates/payments/order_status_page.html`

**Changes for YookassaReceipt scenario:**

1. **Email Input Field (HTML):**
   ```html
   <!-- Email Input Section (for YookassaReceipt scenario) -->
   <div id="email-section" class="email-section hidden">
       <label for="email-input" class="email-label">Email для чека:</label>
       <input 
           type="email" 
           id="email-input" 
           class="email-input" 
           placeholder="example@email.com"
           autocomplete="email"
       >
       <div id="email-error" class="email-error hidden">
           Пожалуйста, введите корректный email
       </div>
       <div id="email-hint" class="email-hint hidden">
           Email обязателен для получения чека
       </div>
   </div>
   ```

2. **CSS Styles:**
   ```css
   .email-section {
       margin-bottom: 24px;
   }
   
   .email-label {
       display: block;
       font-size: 16px;
       font-weight: 500;
       color: #1a1a1a;
       margin-bottom: 8px;
   }
   
   .email-input {
       width: 100%;
       min-height: 48px;
       padding: 12px 16px;
       font-size: 16px;
       border: 2px solid #e0e0e0;
       border-radius: 8px;
       transition: border-color 0.3s ease;
   }
   
   .email-input:focus {
       outline: none;
       border-color: #4a90e2;
   }
   
   .email-input.invalid {
       border-color: #e74c3c;
   }
   
   .email-error {
       color: #e74c3c;
       font-size: 14px;
       margin-top: 8px;
   }
   
   .email-hint {
       color: #666;
       font-size: 14px;
       margin-top: 8px;
   }
   ```

3. **JavaScript Logic:**
   ```javascript
   // Email validation
   function validateEmail(email) {
       const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
       return re.test(email);
   }
   
   // Update UI for YookassaReceipt scenario
   function updateUIForYookassaReceipt(orderData, isReceiptMandatory) {
       if (orderData.status === 'created') {
           const emailSection = document.getElementById('email-section');
           const emailInput = document.getElementById('email-input');
           const emailHint = document.getElementById('email-hint');
           const paymentBtn = document.getElementById('payment-btn');
           
           // Show email section
           emailSection.classList.remove('hidden');
           
           // Show hint if mandatory
           if (isReceiptMandatory) {
               emailHint.classList.remove('hidden');
           }
           
           // Add email validation on input
           emailInput.addEventListener('input', function() {
               const email = emailInput.value.trim();
               const emailError = document.getElementById('email-error');
               
               if (email && !validateEmail(email)) {
                   emailInput.classList.add('invalid');
                   emailError.classList.remove('hidden');
                   if (isReceiptMandatory) {
                       paymentBtn.disabled = true;
                   }
               } else {
                   emailInput.classList.remove('invalid');
                   emailError.classList.add('hidden');
                   if (isReceiptMandatory) {
                       paymentBtn.disabled = !email;
                   }
               }
           });
           
           // Disable payment button if mandatory and no email
           if (isReceiptMandatory) {
               paymentBtn.disabled = true;
           }
       }
   }
   
   // Modified initiatePayment function
   async function initiatePayment() {
       const orderId = document.getElementById('order-id').value;
       const emailInput = document.getElementById('email-input');
       const email = emailInput ? emailInput.value.trim() : null;
       
       // Validate email if provided
       if (email && !validateEmail(email)) {
           alert('Пожалуйста, введите корректный email');
           return;
       }
       
       // ... existing payment initiation logic ...
       // Include email in request body
       body: JSON.stringify({
           order_id: orderId,
           email: email
       })
   }
   ```

#### 3.2 API Endpoint Modifications

**Endpoint:** `GET /v1/order-status/<order_id>`

**Changes:**
Add payment scenario and receipt configuration to response:
```python
@csrf_exempt
def get_order_status(request, order_id):
    # ... existing code ...
    
    # Get payment scenario and receipt config
    device = order.device
    payment_scenario = device.payment_scenario
    is_receipt_mandatory = False
    
    if payment_scenario == 'YookassaReceipt':
        try:
            credentials = MerchantCredentials.objects.get(
                merchant=device.merchant,
                scenario='YookassaReceipt'
            )
            is_receipt_mandatory = credentials.credentials.get('is_receipt_mandatory', False)
        except MerchantCredentials.DoesNotExist:
            pass
    
    data = {
        # ... existing fields ...
        'payment_scenario': payment_scenario,
        'is_receipt_mandatory': is_receipt_mandatory,
    }
    
    return JsonResponse(data, status=200)
```

**Endpoint:** `POST /v1/initiate-payment`

**Changes:**
Accept email parameter and pass to payment scenario:
```python
@csrf_exempt
def initiate_payment(request):
    # ... existing code ...
    
    # Parse email from request
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            order_id = data.get('order_id')
            email = data.get('email')
        else:
            order_id = request.POST.get('order_id')
            email = request.POST.get('email')
    except json.JSONDecodeError:
        # ... error handling ...
    
    # ... existing order retrieval and validation ...
    
    # Execute payment scenario with email
    if device.payment_scenario == 'YookassaReceipt':
        response = PaymentScenarioService.execute_yookassa_receipt_scenario(
            device, order, drink_details, email=email
        )
    else:
        response = PaymentScenarioService.execute_scenario(
            device, order, drink_details
        )
    
    # ... rest of the function ...
```

### 4. Configuration

#### 4.1 Settings

**File:** `coffee_payment/coffee_payment/settings.py`

**Changes:**
```python
# Payment scenarios
PAYMENT_SCENARIOS = ['Yookassa', 'TBank', 'Custom', 'YookassaReceipt']
DEFAULT_PAYMENT_SCENARIO = 'Yookassa'
```

#### 4.2 Merchant Credentials Structure

**Scenario:** YookassaReceipt

**Required Fields:**
- `account_id` (string): Yookassa account ID
- `secret_key` (string): Yookassa secret key
- `is_receipt_mandatory` (boolean): Whether email is required
- `tax_system_code` (integer): Tax system code for receipt

**Optional Fields:**
- `timezone` (integer): Timezone offset for receipt
- `vat_code` (integer): Default VAT code if not in Drink.meta
- `measure` (string): Default measure if not in Drink.meta
- `payment_subject` (string): Default payment subject if not in Drink.meta
- `payment_mode` (string): Default payment mode if not in Drink.meta

**Example:**
```json
{
  "account_id": "1193510",
  "secret_key": "test_Ku1e9ZkX5OoTCm0k2m05Dg66XldJFHkER_9sw5LKE1E",
  "is_receipt_mandatory": true,
  "tax_system_code": 1,
  "timezone": 1,
  "vat_code": 2,
  "measure": "piece",
  "payment_subject": "commodity",
  "payment_mode": "full_payment"
}
```

## Data Models

### Drink Model

**Fields:**
- `id` (Integer, PK): Drink identifier matching device data
- `name` (String): Drink name
- `description` (Text): Drink description
- `prices` (JSON): Price mapping by size
- `available` (Boolean): Availability flag
- `meta` (JSON, nullable): Receipt metadata

**Meta Structure:**
```json
{
  "vat_code": 2,
  "measure": "piece",
  "payment_subject": "commodity",
  "payment_mode": "full_payment"
}
```

### Receipt Model

**Fields:**
- `id` (UUID, PK): Receipt identifier
- `order` (FK to Order): Associated order
- `contact` (String): Customer email
- `drink_no` (String, nullable): Drink identifier
- `amount` (Decimal): Payment amount
- `receipt_data` (JSON, nullable): Complete receipt data
- `sent_at` (DateTime, nullable): When receipt was sent
- `status` (String): Receipt status (pending/sent/failed)
- `created_at` (DateTime): Creation timestamp

## Error Handling

### Email Validation Errors

**Client-Side:**
- Display inline error message below email input
- Disable payment button if email is mandatory and invalid
- Use red border color for invalid input

**Server-Side:**
- Validate email format in initiate_payment view
- Return 400 error with user-friendly message if invalid
- Log validation failures

### Missing Credentials

**Scenario:** YookassaReceipt credentials not configured for merchant

**Handling:**
- Catch ValueError in execute_yookassa_receipt_scenario
- Update order status to 'failed'
- Return error page with message from ERROR_MESSAGES
- Log error with merchant and device details

### Receipt Creation Failures

**Scenario:** Yookassa API rejects receipt data

**Handling:**
- Log complete receipt object and API error response
- Update order status to 'failed'
- Do not create Receipt record
- Return error to user

### Drink Not Found

**Scenario:** Drink with specified ID doesn't exist

**Handling:**
- Use fallback values from merchant credentials
- Log warning about missing drink
- Continue with payment creation
- Receipt will use only credential-based values

## Testing Strategy

### Unit Tests

**File:** `coffee_payment/tests/test_yookassa_receipt.py`

**Test Cases:**

1. **test_build_receipt_object_with_drink_meta**
   - Verify receipt uses values from drink_meta when available

2. **test_build_receipt_object_with_credential_fallback**
   - Verify receipt uses credential values when drink_meta missing

3. **test_build_receipt_object_excludes_missing_fields**
   - Verify fields not in drink_meta or credentials are excluded

4. **test_email_validation**
   - Test valid and invalid email formats

5. **test_receipt_mandatory_validation**
   - Verify payment blocked when email required but not provided

6. **test_receipt_optional_validation**
   - Verify payment proceeds without email when optional

7. **test_save_receipt_record**
   - Verify Receipt model is created with correct data

8. **test_drink_id_migration**
   - Verify Drink model works with integer IDs

### Integration Tests

**File:** `coffee_payment/tests/test_yookassa_receipt_integration.py`

**Test Cases:**

1. **test_full_payment_flow_with_receipt**
   - End-to-end test: QR scan → email input → payment → receipt creation

2. **test_payment_flow_without_email**
   - Test optional email scenario

3. **test_missing_credentials_handling**
   - Verify error handling when credentials not configured

4. **test_yookassa_api_integration**
   - Test actual API call with receipt (using test credentials)

### Manual Testing

**Test Scenarios:**

1. **Email Input Validation:**
   - Enter invalid email formats
   - Verify inline error messages
   - Verify button state changes

2. **Mandatory vs Optional Email:**
   - Test with is_receipt_mandatory=true
   - Test with is_receipt_mandatory=false
   - Verify button behavior

3. **Receipt Data Fallback:**
   - Create drink with partial meta
   - Verify credential fallback works
   - Check Yookassa receipt data

4. **Mobile Responsiveness:**
   - Test email input on mobile devices
   - Verify keyboard behavior
   - Check layout on different screen sizes

## Migration Strategy

### Database Migrations

**Migration 1: Add meta field to Drink**
```python
operations = [
    migrations.AddField(
        model_name='drink',
        name='meta',
        field=models.JSONField(blank=True, null=True, help_text='...'),
    ),
]
```

**Migration 2: Change Drink ID to Integer**
```python
# This is a complex migration requiring data migration
# Steps:
# 1. Create new integer ID field
# 2. Populate with sequential IDs
# 3. Update foreign keys
# 4. Remove old UUID field
# 5. Rename new field to 'id'
```

**Migration 3: Enhance Receipt Model**
```python
operations = [
    migrations.AddField(
        model_name='receipt',
        name='drink_no',
        field=models.CharField(max_length=255, null=True, blank=True),
    ),
    migrations.AddField(
        model_name='receipt',
        name='amount',
        field=models.DecimalField(max_digits=10, decimal_places=2, default=0),
        preserve_default=False,
    ),
    migrations.AddField(
        model_name='receipt',
        name='receipt_data',
        field=models.JSONField(blank=True, null=True, help_text='...'),
    ),
    migrations.AddField(
        model_name='receipt',
        name='created_at',
        field=models.DateTimeField(auto_now_add=True, default=timezone.now),
        preserve_default=False,
    ),
]
```

### Deployment Steps

1. **Pre-deployment:**
   - Backup database
   - Document existing Drink IDs
   - Prepare data migration script

2. **Deployment:**
   - Run migrations
   - Execute data migration for Drink IDs
   - Verify data integrity

3. **Post-deployment:**
   - Test YookassaReceipt scenario
   - Monitor logs for errors
   - Verify receipt creation

## Security Considerations

### Email Privacy

- Store emails only in Receipt model
- Do not log email addresses in plain text
- Consider GDPR compliance for email storage

### Credential Security

- Yookassa credentials stored encrypted in database
- Never log secret_key values
- Use environment variables for sensitive data

### Input Validation

- Validate email format on client and server
- Sanitize all user inputs
- Prevent injection attacks in receipt data

## Performance Considerations

### Database Queries

- Use select_related for Order → Device → Merchant queries
- Index Receipt.order_id for fast lookups
- Consider caching merchant credentials

### API Calls

- Yookassa API call adds ~500ms to payment flow
- No additional API calls compared to base Yookassa scenario
- Receipt data increases payload size by ~200 bytes

### Frontend Performance

- Email validation is client-side (no server round-trip)
- Minimal JavaScript overhead (~50 lines)
- No additional HTTP requests

## Logging

### Log Events

1. **Receipt Object Construction:**
   ```python
   log_info(
       f"Building receipt object for Order {order.id}. "
       f"Email: {email[:3]}***@***, has_drink_meta: {bool(drink_meta)}",
       'yookassa_receipt_service'
   )
   ```

2. **Receipt Creation:**
   ```python
   log_info(
       f"Receipt created for Order {order.id}. "
       f"Receipt ID: {receipt.id}, Amount: {receipt.amount}",
       'yookassa_receipt_service'
   )
   ```

3. **Fallback Usage:**
   ```python
   log_info(
       f"Using credential fallback for field '{field_name}' in Order {order.id}",
       'yookassa_receipt_service'
   )
   ```

4. **Validation Errors:**
   ```python
   log_error(
       f"Invalid email format for Order {order.id}: {email}",
       'initiate_payment',
       'ERROR'
   )
   ```

## Documentation Updates

### PROJECT.md Updates

Add section describing YookassaReceipt scenario:

```markdown
## YookassaReceipt Payment Scenario

The YookassaReceipt scenario extends the base Yookassa scenario with fiscal receipt generation capabilities.

### Features

- Email collection for receipt delivery
- Configurable mandatory/optional email requirement
- Flexible receipt metadata with fallback logic
- Automatic receipt record creation

### Configuration

Merchant credentials for YookassaReceipt include:
- `is_receipt_mandatory`: Whether email is required
- `tax_system_code`: Tax system code for fiscal compliance
- Optional fallback values for VAT, measure, payment subject/mode

### Receipt Data Flow

1. Customer provides email on order status page
2. System builds receipt object using drink metadata and credential fallbacks
3. Receipt data sent to Yookassa with payment request
4. Receipt record saved to database for audit trail
```

## Future Enhancements

1. **Receipt Delivery Tracking:**
   - Monitor Yookassa receipt delivery status
   - Update Receipt.status based on delivery confirmation

2. **Email Verification:**
   - Send verification code before payment
   - Reduce fraudulent email addresses

3. **Receipt Templates:**
   - Customizable receipt formats per merchant
   - Branding options for receipts

4. **Bulk Receipt Management:**
   - Admin interface for viewing all receipts
   - Export receipts for accounting

5. **SMS Receipt Option:**
   - Alternative to email for receipt delivery
   - Phone number collection and validation
