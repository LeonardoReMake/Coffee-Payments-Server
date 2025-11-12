# Design Document: Order Information Screen

## Overview

This design document describes the implementation of an order information screen that displays order details to users before payment in Yookassa and TBank payment scenarios. The screen will be inserted into the existing payment flow between drink price retrieval and payment creation, providing transparency and allowing users to review their order before committing to payment.

### Key Design Principles

- **MVP Approach**: Minimal implementation that satisfies requirements
- **Mobile-First**: Responsive design optimized for mobile devices
- **Existing Patterns**: Leverage existing project structure (templates, logging, error handling)
- **Centralized Messages**: User-facing error messages stored in a dedicated file

## Architecture

### Current Payment Flow

```
User scans QR → qr_code_redirect() → validate device/merchant → 
redirect to payment processor → yookassa_payment_process() → 
get drink price from Tmetr API → create order → execute payment scenario → 
redirect to payment provider
```

### New Payment Flow (Yookassa & TBank only)

```
User scans QR → qr_code_redirect() → validate device/merchant → 
redirect to payment processor → yookassa_payment_process() → 
get drink price from Tmetr API → create order → 
[NEW] render order_info_screen.html → user clicks "Перейти к оплате" → 
[NEW] initiate_payment() → execute payment scenario → 
redirect to payment provider
```

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Payment Flow Layer                        │
├─────────────────────────────────────────────────────────────┤
│  qr_code_redirect() → yookassa_payment_process()            │
│         ↓                                                    │
│  [NEW] show_order_info() ← drink_details, device, order     │
│         ↓                                                    │
│  [NEW] initiate_payment() → PaymentScenarioService          │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                        │
├─────────────────────────────────────────────────────────────┤
│  [NEW] order_info_screen.html                               │
│    - Displays: logo, location, drink info, price            │
│    - States: loading, success, error                        │
│    - Button: "Перейти к оплате"                             │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                                │
├─────────────────────────────────────────────────────────────┤
│  [NEW] user_messages.py - Centralized error messages        │
│  Device model - logo_url, client_info fields                │
│  Order model - existing fields                              │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. View Functions (payments/views.py)

#### Modified: `yookassa_payment_process()`

**Current Behavior**: Creates order and immediately executes payment scenario

**New Behavior**: 
- For Yookassa/TBank scenarios: Create order, then render order info screen
- For Custom scenario: Keep existing behavior (direct redirect)

**Changes**:
```python
# After creating order with status='created'
if device.payment_scenario in ['Yookassa', 'TBank']:
    return show_order_info(request, device, order, drink_details)
else:
    # Execute Custom scenario immediately
    return PaymentScenarioService.execute_scenario(device, order, drink_details)
```

#### New: `show_order_info(request, device, order, drink_details)`

**Purpose**: Render the order information screen

**Parameters**:
- `request`: HttpRequest object
- `device`: Device instance
- `order`: Order instance (status='created')
- `drink_details`: Dict with drink information from Tmetr API

**Returns**: HttpResponse with rendered template

**Logic**:
1. Extract drink information from drink_details
2. Map drink size (0,1,2) to Russian labels (маленький, средний, большой)
3. Format price for display (kopecks to rubles)
4. Prepare context with all required data
5. Log the screen rendering event
6. Render order_info_screen.html template

**Context Data**:
```python
{
    'device': device,
    'order': order,
    'drink_name': drink_details.get('name', order.drink_name),
    'drink_size': size_label,  # маленький/средний/большой
    'drink_price': order.price / 100,  # Convert to rubles
    'logo_url': device.logo_url,
    'location': device.location,
    'client_info': device.client_info,
    'payment_scenario': device.payment_scenario
}
```

#### New: `initiate_payment(request)`

**Purpose**: Handle payment initiation from order info screen

**Method**: POST

**Parameters** (from POST data):
- `order_id`: UUID of the order

**Returns**: 
- Success: HttpResponseRedirect to payment provider
- Error: JSON response with error message

**Logic**:
1. Validate order_id parameter
2. Retrieve Order instance
3. Check if order has expired
4. Execute payment scenario via PaymentScenarioService
5. Log payment initiation with all parameters
6. Handle errors and return appropriate responses

**Error Handling**:
- Missing order_id: 400 Bad Request
- Order not found: 404 Not Found
- Order expired: 400 Bad Request with user-friendly message
- Payment creation failed: 503 Service Unavailable

### 2. Template (templates/payments/order_info_screen.html)

**Purpose**: Display order information and payment button

**Design Requirements**:
- Mobile-first responsive design
- Support screen widths 320px - 1920px
- Display loading, success, and error states
- Clean, minimal UI following MVP principles

**Structure**:
```html
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Информация о заказе</title>
    <style>
        /* Mobile-first CSS with responsive breakpoints */
    </style>
</head>
<body>
    <div class="container">
        <!-- Logo (if available) -->
        <div class="logo-section">
            <img src="{{ logo_url }}" alt="Логотип">
        </div>
        
        <!-- Order Information -->
        <div class="order-info">
            <h1>Ваш заказ</h1>
            <div class="info-row">
                <span class="label">Адрес:</span>
                <span class="value">{{ location }}</span>
            </div>
            <div class="info-row">
                <span class="label">Напиток:</span>
                <span class="value">{{ drink_name }}</span>
            </div>
            <div class="info-row">
                <span class="label">Размер:</span>
                <span class="value">{{ drink_size }}</span>
            </div>
            <div class="info-row price">
                <span class="label">Цена:</span>
                <span class="value">{{ drink_price }} ₽</span>
            </div>
        </div>
        
        <!-- Client Info (if available) -->
        {% if client_info %}
        <div class="client-info">
            <p>{{ client_info }}</p>
        </div>
        {% endif %}
        
        <!-- Payment Button -->
        <button id="payment-button" onclick="initiatePayment()">
            Перейти к оплате
        </button>
        
        <!-- Loading State -->
        <div id="loading-state" style="display: none;">
            <div class="spinner"></div>
            <p>Создание платежа...</p>
        </div>
        
        <!-- Error State -->
        <div id="error-state" style="display: none;">
            <p class="error-message"></p>
            <button onclick="retryPayment()">Попробовать снова</button>
        </div>
    </div>
    
    <script>
        // JavaScript for payment initiation and state management
    </script>
</body>
</html>
```

**JavaScript Functionality**:
- `initiatePayment()`: Send POST request to initiate_payment endpoint
- Show loading state during request
- Handle success: redirect to payment URL
- Handle error: display user-friendly message from centralized file
- `retryPayment()`: Reset UI and allow retry

**CSS Approach**:
- Mobile-first with min-width media queries
- Flexbox for layout
- CSS Grid for info rows
- Simple loading spinner animation
- Accessible color contrast
- Touch-friendly button sizes (min 44px height)

### 3. User Messages File (payments/user_messages.py)

**Purpose**: Centralized storage for all user-facing messages

**Structure**:
```python
"""
Centralized user-facing messages for the payment system.
All messages shown to end users should be defined here.
"""

ERROR_MESSAGES = {
    'order_not_found': 'Заказ не найден. Пожалуйста, отсканируйте QR-код снова.',
    'order_expired': 'Время заказа истекло. Пожалуйста, создайте новый заказ.',
    'payment_creation_failed': 'Не удалось создать платеж. Пожалуйста, попробуйте позже.',
    'service_unavailable': 'Сервис временно недоступен. Пожалуйста, попробуйте позже.',
    'invalid_request': 'Некорректный запрос. Пожалуйста, попробуйте снова.',
    'missing_credentials': 'Платежная система не настроена. Обратитесь к администратору.',
}

INFO_MESSAGES = {
    'loading_payment': 'Создание платежа...',
    'redirecting': 'Перенаправление на страницу оплаты...',
}
```

**Usage**:
```python
from payments.user_messages import ERROR_MESSAGES

error_msg = ERROR_MESSAGES['order_expired']
return JsonResponse({'error': error_msg}, status=400)
```

### 4. Model Changes (payments/models.py)

**Device Model - New Fields**:

```python
class Device(models.Model):
    # ... existing fields ...
    
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
```

**Migration Required**: Yes, to add logo_url and client_info fields

### 5. URL Configuration (coffee_payment/urls.py)

**New URL Pattern**:
```python
path('v1/initiate-payment', initiate_payment, name='initiate_payment'),
```

## Data Models

### Device Model Extensions

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| logo_url | URLField | Yes | URL to merchant logo image |
| client_info | TextField | Yes | Custom message for customers |

### Order Model (No Changes)

Existing Order model fields are sufficient:
- id (UUID)
- drink_name
- device (FK)
- merchant (FK)
- size (1=Small, 2=Medium, 3=Large)
- price (Decimal, in kopecks)
- status (created, pending, paid, etc.)
- expires_at (DateTime)

### Context Data Structure

Data passed to order_info_screen.html template:

```python
{
    'device': Device,           # Device instance
    'order': Order,             # Order instance
    'drink_name': str,          # Drink name
    'drink_size': str,          # маленький/средний/большой
    'drink_price': float,       # Price in rubles (e.g., 50.00)
    'logo_url': str | None,     # URL to logo or None
    'location': str,            # Device location
    'client_info': str | None,  # Custom message or None
    'payment_scenario': str     # Yookassa or TBank
}
```

## Error Handling

### Error Categories

1. **Validation Errors** (400 Bad Request)
   - Missing order_id parameter
   - Invalid order_id format
   - Order expired

2. **Not Found Errors** (404 Not Found)
   - Order does not exist

3. **Service Errors** (503 Service Unavailable)
   - Payment provider API failure
   - Network timeout
   - Missing credentials

### Error Response Format

**JSON Response** (for AJAX requests):
```json
{
    "error": "User-friendly error message from user_messages.py",
    "code": "order_expired"
}
```

**HTML Response** (for direct navigation):
- Render error_page.html with user-friendly message

### Error Logging

All errors must be logged with:
- Order ID
- Device UUID
- Payment scenario
- Error details
- Request parameters

Example:
```python
log_error(
    f"Payment initiation failed for Order {order.id}: {str(e)}. "
    f"Scenario: {device.payment_scenario}, Device: {device.device_uuid}",
    'initiate_payment',
    'ERROR'
)
```

## Testing Strategy

### Unit Tests

**Test File**: `coffee_payment/tests/test_order_info_screen.py`

**Test Cases**:

1. **test_show_order_info_yookassa_scenario**
   - Verify order info screen is rendered for Yookassa scenario
   - Check all context data is present
   - Verify correct template is used

2. **test_show_order_info_tbank_scenario**
   - Verify order info screen is rendered for TBank scenario
   - Check all context data is present

3. **test_custom_scenario_skips_order_info**
   - Verify Custom scenario bypasses order info screen
   - Check direct redirect to custom URL

4. **test_initiate_payment_success**
   - Mock successful payment creation
   - Verify redirect to payment provider URL
   - Check order status updated to 'pending'

5. **test_initiate_payment_expired_order**
   - Create expired order
   - Verify 400 response with appropriate error message
   - Check order status remains 'created'

6. **test_initiate_payment_missing_order_id**
   - Send request without order_id
   - Verify 400 response

7. **test_initiate_payment_order_not_found**
   - Send request with non-existent order_id
   - Verify 404 response

8. **test_drink_size_mapping**
   - Verify size 0 → маленький
   - Verify size 1 → средний
   - Verify size 2 → большой

9. **test_price_formatting**
   - Verify kopecks to rubles conversion
   - Check decimal formatting

10. **test_logo_url_optional**
    - Verify screen renders without logo_url
    - Check no errors when logo_url is None

11. **test_client_info_optional**
    - Verify screen renders without client_info
    - Check section is hidden when client_info is None

### Integration Tests

**Test File**: `coffee_payment/tests/test_order_info_integration.py`

**Test Cases**:

1. **test_full_payment_flow_yookassa**
   - Simulate complete flow from QR scan to payment
   - Verify order info screen appears
   - Mock payment initiation
   - Check final redirect

2. **test_full_payment_flow_tbank**
   - Same as above for TBank scenario

3. **test_payment_scenario_routing**
   - Test all three scenarios (Yookassa, TBank, Custom)
   - Verify correct behavior for each

### Manual Testing Checklist

- [ ] Order info screen displays correctly on mobile (320px width)
- [ ] Order info screen displays correctly on tablet (768px width)
- [ ] Order info screen displays correctly on desktop (1920px width)
- [ ] Logo displays when logo_url is set
- [ ] Logo section is hidden when logo_url is None
- [ ] Client info displays when client_info is set
- [ ] Client info section is hidden when client_info is None
- [ ] Loading state appears when payment button is clicked
- [ ] Error state appears when payment creation fails
- [ ] Retry button works after error
- [ ] Payment button is disabled during loading
- [ ] All text is readable and properly formatted
- [ ] Price displays in rubles with 2 decimal places
- [ ] Drink size displays in Russian
- [ ] Custom scenario bypasses order info screen

## Implementation Notes

### Size Mapping

Current system uses 0-indexed sizes in URLs (0, 1, 2) but 1-indexed in database (1, 2, 3).

**Mapping for Display**:
```python
SIZE_LABELS = {
    1: 'маленький',
    2: 'средний',
    3: 'большой'
}
```

### Price Formatting

Prices are stored in kopecks (integer) but displayed in rubles (decimal).

**Conversion**:
```python
price_rubles = order.price / 100
formatted_price = f"{price_rubles:.2f} ₽"
```

### Logging Standards

Follow existing project logging patterns:

```python
from payments.utils.logging import log_info, log_error

# Info logging
log_info(
    f"Rendering order info screen for Order {order.id}, "
    f"Device {device.device_uuid}, Scenario {device.payment_scenario}",
    'show_order_info'
)

# Error logging
log_error(
    f"Failed to initiate payment for Order {order.id}: {str(e)}",
    'initiate_payment',
    'ERROR'
)
```

### CSRF Protection

The initiate_payment view must handle CSRF tokens:

```python
@csrf_exempt  # Only if handling external webhooks
def initiate_payment(request):
    # Or include {% csrf_token %} in form
```

For AJAX requests from order_info_screen.html, include CSRF token in headers:

```javascript
fetch('/v1/initiate-payment', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
    },
    body: JSON.stringify({order_id: orderId})
})
```

### Responsive Breakpoints

```css
/* Mobile: 320px - 767px (default) */
/* Tablet: 768px - 1023px */
@media (min-width: 768px) { ... }

/* Desktop: 1024px+ */
@media (min-width: 1024px) { ... }
```

## Security Considerations

1. **Order Validation**: Always verify order belongs to the device and hasn't expired
2. **CSRF Protection**: Include CSRF tokens in all POST requests
3. **Input Sanitization**: Validate and sanitize all user inputs
4. **Error Messages**: Never expose technical details or stack traces to users
5. **Logging**: Log all payment attempts for audit trail

## Performance Considerations

1. **Image Loading**: Use lazy loading for logo images
2. **Caching**: Consider caching device information
3. **Database Queries**: Minimize queries by using select_related for device/merchant
4. **Timeout**: Set reasonable timeout for payment creation requests (30 seconds)

## Deployment Considerations

1. **Database Migration**: Run migration to add logo_url and client_info fields
2. **Static Files**: Ensure CSS is properly served
3. **Logging**: Verify log file permissions and rotation
4. **Environment Variables**: No new environment variables required
5. **Backward Compatibility**: Custom scenario behavior unchanged

## Future Enhancements (Out of Scope for MVP)

- QR code display on order screen for mobile payment apps
- Order history for returning customers
- Drink customization options
- Promotional codes or discounts
- Multi-language support
- Analytics tracking for conversion rates
- A/B testing different screen layouts
