# Design Document

## Overview

The Order Status Page is a real-time tracking interface that displays order information and dynamically updates the order status without page reloads. Users are redirected to this page by the payment system after completing payment. The page polls the backend API every second to fetch the latest order status and updates the UI accordingly with smooth transitions between different states (loading, success, error).

The design follows the existing architecture patterns in the Coffee Payment Server, reusing components like the centralized error message system, logging utilities, and mobile-first responsive design principles established in the order_info_screen.

## Architecture

### High-Level Flow

```
Payment System Redirect
        ↓
Order Status Page Load
        ↓
Extract order_id from URL
        ↓
Initial Order Data Fetch (GET /v1/order-status/<order_id>)
        ↓
Render Initial UI State
        ↓
Start Status Polling (every 1 second)
        ↓
    ┌─────────────────────┐
    │  Poll Order Status  │
    │  (GET /v1/order-    │
    │   status/<order_id>)│
    └─────────────────────┘
        ↓
    ┌─────────────────────┐
    │  Update UI Based    │
    │  on Status          │
    └─────────────────────┘
        ↓
    Status in [pending, paid, make_pending]?
        ↓ Yes              ↓ No
    Continue Polling    Stop Polling
```

### Component Architecture

The implementation consists of three main components:

1. **Backend API Endpoint** (`/v1/order-status/<order_id>`)
   - Retrieves order data from database
   - Returns JSON response with order details and status
   - Handles error cases (order not found, invalid ID)

2. **View Function** (`/v1/order-status-page`)
   - Renders the HTML template
   - Passes order_id to template from query parameters
   - Handles initial page load errors

3. **Frontend Template** (`order_status_page.html`)
   - Displays order information
   - Implements status polling logic
   - Manages UI state transitions
   - Handles retry payment functionality

## Components and Interfaces

### 1. Backend API Endpoint

**Endpoint:** `GET /v1/order-status/<order_id>`

**Purpose:** Provide order status data for polling

**Request:**
- Method: GET
- URL Parameter: `order_id` (string, required)
- Headers: None required

**Response (Success - 200):**
```json
{
  "order_id": "20250317110122659ba6d7-9ace-cndn",
  "status": "paid",
  "drink_name": "Американо",
  "drink_size": "средний",
  "price": 150.00,
  "device": {
    "location": "ул. Ленина, 10",
    "logo_url": "https://example.com/logo.png",
    "client_info_pending": "Ожидайте подтверждения оплаты...",
    "client_info_paid": "Спасибо за оплату!",
    "client_info_not_paid": "Свяжитесь с поддержкой: <a href='tel:+79001234567'>+7 900 123-45-67</a>",
    "client_info_make_pending": "Ваш напиток готовится...",
    "client_info_successful": "Приятного аппетита!"
  }
}
```

**Response (Error - 404):**
```json
{
  "error": "Заказ не найден. Пожалуйста, отсканируйте QR-код снова."
}
```

**Implementation:**
```python
@csrf_exempt
def get_order_status(request, order_id):
    """
    API endpoint to retrieve order status for polling.
    
    Args:
        request: HttpRequest object
        order_id: Order ID from URL parameter
    
    Returns:
        JsonResponse with order data or error message
    """
    from django.http import JsonResponse
    from payments.user_messages import ERROR_MESSAGES
    
    try:
        order = Order.objects.select_related('device').get(id=order_id)
    except Order.DoesNotExist:
        log_error(f"Order not found: {order_id}", 'get_order_status', 'ERROR')
        return JsonResponse(
            {'error': ERROR_MESSAGES['order_not_found']},
            status=404
        )
    
    # Size mapping
    SIZE_LABELS = {1: 'маленький', 2: 'средний', 3: 'большой'}
    
    # Prepare response data
    data = {
        'order_id': order.id,
        'status': order.status,
        'drink_name': order.drink_name,
        'drink_size': SIZE_LABELS.get(order.size, 'неизвестный размер'),
        'price': float(order.price / 100),  # Convert kopecks to rubles
        'device': {
            'location': order.device.location,
            'logo_url': order.device.logo_url,
            'client_info_pending': order.device.client_info_pending,
            'client_info_paid': order.device.client_info_paid,
            'client_info_not_paid': order.device.client_info_not_paid,
            'client_info_make_pending': order.device.client_info_make_pending,
            'client_info_successful': order.device.client_info_successful,
        }
    }
    
    return JsonResponse(data, status=200)
```

### 2. View Function for Page Rendering

**Endpoint:** `GET /v1/order-status-page?order_id=<order_id>`

**Purpose:** Render the order status page HTML

**Request:**
- Method: GET
- Query Parameter: `order_id` (string, required)

**Response:**
- HTML page with embedded order_id
- Error page if order_id is missing or invalid

**Implementation:**
```python
def show_order_status_page(request):
    """
    Render the order status tracking page.
    
    Args:
        request: HttpRequest object with order_id query parameter
    
    Returns:
        HttpResponse with rendered order_status_page.html template
    """
    from payments.user_messages import ERROR_MESSAGES
    
    order_id = request.GET.get('order_id')
    
    if not order_id:
        log_error(
            "Missing order_id parameter in order status page request",
            'show_order_status_page',
            'ERROR'
        )
        return render_error_page(ERROR_MESSAGES['missing_order_id'], 400)
    
    # Verify order exists before rendering page
    try:
        order = Order.objects.select_related('device').get(id=order_id)
    except Order.DoesNotExist:
        log_error(
            f"Order not found: {order_id}",
            'show_order_status_page',
            'ERROR'
        )
        return render_error_page(ERROR_MESSAGES['order_not_found'], 404)
    
    log_info(
        f"Rendering order status page for Order {order_id}",
        'show_order_status_page'
    )
    
    context = {
        'order_id': order_id
    }
    
    return render(request, 'payments/order_status_page.html', context)
```

### 3. Frontend Template

**File:** `templates/payments/order_status_page.html`

**Key Features:**
- Mobile-first responsive design (320px - 1920px)
- Status polling every 1 second
- Smooth UI transitions between states
- HTML rendering support for client info fields
- Retry payment functionality for not_paid status

**UI States:**

1. **Loading State** (Initial and during polling)
   - Spinner animation
   - "Загрузка информации о заказе..." message

2. **Status-Specific States:**
   - **pending**: Loading spinner + "Проверяем оплату заказа..."
   - **paid**: Success icon + "Заказ успешно оплачен, начинаем готовить"
   - **not_paid**: Error icon + "Оплата не прошла" + "Повторить оплату" button
   - **make_pending**: Loading spinner + "Готовим напиток..."
   - **successful**: Success icon + "Напиток готов"

3. **Error State** (Network or API errors)
   - Error message
   - "Попробовать снова" button

**JavaScript Functions:**

```javascript
// Fetch order status from API
async function fetchOrderStatus(orderId) {
    const response = await fetch(`/v1/order-status/${orderId}`);
    if (!response.ok) {
        throw new Error('Failed to fetch order status');
    }
    return await response.json();
}

// Update UI based on order status
function updateUI(orderData) {
    // Update order information
    // Update status-specific display
    // Show/hide retry button for not_paid status
    // Render HTML in client info fields
}

// Start status polling
function startPolling(orderId) {
    const intervalId = setInterval(async () => {
        try {
            const data = await fetchOrderStatus(orderId);
            updateUI(data);
            
            // Stop polling for terminal statuses
            if (['successful', 'not_paid', 'failed'].includes(data.status)) {
                clearInterval(intervalId);
            }
        } catch (error) {
            showError('Не удалось обновить статус заказа');
        }
    }, 1000);
}

// Retry payment (for not_paid status)
function retryPayment(orderId) {
    // Same logic as order_info_screen.html
    // POST to /v1/initiate-payment with order_id
}
```

## Data Models

### Existing Models (No Changes Required)

**Order Model:**
- Already contains all required fields
- Status field supports all needed statuses

**Device Model:**
- Needs new fields for status-specific client information

### Required Model Changes

Add new fields to Device model:

```python
class Device(models.Model):
    # ... existing fields ...
    
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
```

**Migration:** Create a new migration file to add these fields.

### User Messages

Add new messages to `user_messages.py`:

```python
ERROR_MESSAGES = {
    # ... existing messages ...
    'status_update_failed': 'Не удалось обновить статус заказа. Пожалуйста, обновите страницу.',
}

INFO_MESSAGES = {
    # ... existing messages ...
    'loading_order_info': 'Загрузка информации о заказе...',
}

STATUS_DESCRIPTIONS = {
    'pending': 'Проверяем оплату заказа...',
    'paid': 'Заказ успешно оплачен, начинаем готовить',
    'not_paid': 'Оплата не прошла',
    'make_pending': 'Готовим напиток...',
    'successful': 'Напиток готов',
    'failed': 'Произошла ошибка при обработке заказа',
}
```

## Error Handling

### Backend Error Handling

1. **Order Not Found (404)**
   - Return JSON error response
   - Log error with order_id

2. **Invalid Order ID (400)**
   - Return JSON error response
   - Log error with provided ID

3. **Database Errors (500)**
   - Return generic error message
   - Log detailed error for debugging

### Frontend Error Handling

1. **Network Errors**
   - Show error message to user
   - Provide "Попробовать снова" button
   - Log error to console

2. **API Errors (4xx, 5xx)**
   - Parse error message from response
   - Display user-friendly message
   - Log error to console

3. **Polling Failures**
   - Continue showing last known status
   - Display warning message
   - Allow manual refresh

## Testing Strategy

### Unit Tests

**Test File:** `coffee_payment/tests/test_order_status_page.py`

**Test Cases:**

1. **API Endpoint Tests:**
   - Test successful order status retrieval
   - Test order not found error
   - Test invalid order ID error
   - Test response data structure
   - Test size label mapping
   - Test price conversion (kopecks to rubles)

2. **View Function Tests:**
   - Test successful page rendering
   - Test missing order_id parameter
   - Test order not found error
   - Test context data passed to template

3. **Model Tests:**
   - Test new Device fields are nullable
   - Test HTML content in client info fields

### Integration Tests

**Test File:** `coffee_payment/tests/test_order_status_integration.py`

**Test Cases:**

1. **End-to-End Status Flow:**
   - Create order with 'pending' status
   - Fetch status via API
   - Update order status to 'paid'
   - Verify API returns updated status
   - Continue through all statuses

2. **Retry Payment Flow:**
   - Create order with 'not_paid' status
   - Render status page
   - Simulate retry payment button click
   - Verify payment initiation request

3. **Polling Behavior:**
   - Verify polling continues for active statuses
   - Verify polling stops for terminal statuses

### Manual Testing Checklist

1. **Mobile Responsiveness:**
   - Test on 320px, 375px, 768px, 1024px, 1920px widths
   - Verify touch targets are at least 44px
   - Verify text is readable without zooming

2. **Status Transitions:**
   - Verify smooth transitions between states
   - Verify correct icons and messages for each status
   - Verify HTML rendering in client info fields

3. **Retry Payment:**
   - Verify button appears only for not_paid status
   - Verify payment initiation works correctly
   - Verify error handling for failed payment creation

4. **Accessibility:**
   - Test with screen reader
   - Test keyboard navigation
   - Test high contrast mode
   - Test reduced motion preference

## URL Routing

Add new routes to `coffee_payment/urls.py`:

```python
urlpatterns = [
    # ... existing routes ...
    
    # Order status page (HTML)
    path('v1/order-status-page', views.show_order_status_page, name='order_status_page'),
    
    # Order status API (JSON)
    path('v1/order-status/<str:order_id>', views.get_order_status, name='get_order_status'),
]
```

## Payment System Integration

### Redirect URL Configuration

When creating payments in Yookassa or TBank, configure the success redirect URL to point to the order status page:

**Yookassa:**
```python
confirmation = {
    'type': 'redirect',
    'return_url': f'https://{domain}/v1/order-status-page?order_id={order.id}'
}
```

**TBank:**
```python
success_url = f'https://{domain}/v1/order-status-page?order_id={order.id}'
```

This ensures users are automatically redirected to the status tracking page after completing payment.

## Performance Considerations

### Backend Optimization

1. **Database Query Optimization:**
   - Use `select_related('device')` to avoid N+1 queries
   - Consider caching order data for 1-2 seconds to reduce database load

2. **API Response Size:**
   - Return only necessary fields
   - Compress response if supported by client

### Frontend Optimization

1. **Polling Frequency:**
   - 1 second interval balances responsiveness and server load
   - Stop polling for terminal statuses to reduce unnecessary requests

2. **UI Performance:**
   - Use CSS transitions for smooth state changes
   - Minimize DOM manipulations during updates
   - Debounce retry button clicks

## Security Considerations

1. **Order ID Validation:**
   - Validate order_id format and length
   - Prevent SQL injection through ORM usage

2. **CSRF Protection:**
   - API endpoint is read-only (GET), no CSRF token required
   - Retry payment uses existing CSRF-protected endpoint

3. **Rate Limiting:**
   - Consider implementing rate limiting for status API
   - Prevent abuse through excessive polling

## Accessibility

1. **Screen Reader Support:**
   - Use semantic HTML elements
   - Provide ARIA labels for status indicators
   - Announce status changes dynamically

2. **Keyboard Navigation:**
   - Ensure all interactive elements are keyboard accessible
   - Provide visible focus indicators

3. **Visual Accessibility:**
   - Maintain sufficient color contrast (WCAG AA)
   - Support high contrast mode
   - Provide text alternatives for icons

4. **Motion Accessibility:**
   - Respect `prefers-reduced-motion` preference
   - Provide alternative to spinner animation

## Deployment Considerations

1. **Database Migration:**
   - Run migration to add new Device fields
   - No data migration required (fields are nullable)

2. **Payment System Configuration:**
   - Update return URLs in Yookassa/TBank settings
   - Test redirect flow in staging environment

3. **Monitoring:**
   - Monitor API endpoint response times
   - Track polling request volume
   - Alert on high error rates

## Future Enhancements

1. **WebSocket Support:**
   - Replace polling with WebSocket for real-time updates
   - Reduce server load and improve responsiveness

2. **Push Notifications:**
   - Notify users when drink is ready
   - Reduce need to keep page open

3. **Order History:**
   - Allow users to view past orders
   - Provide receipt download functionality

4. **Internationalization:**
   - Support multiple languages
   - Localize status messages and UI text
