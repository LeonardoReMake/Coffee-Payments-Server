# Design Document

## Overview

Данный дизайн описывает объединение двух существующих экранов (`order_info_screen.html` и `order_status_page.html`) в единую универсальную страницу отслеживания статуса заказа. Новая страница будет динамически адаптироваться к текущему статусу заказа, отображая соответствующий UI и функциональность.

Ключевые преимущества:
- Устранение дублирования кода между двумя шаблонами
- Единая точка входа для всех статусов заказа
- Возможность возврата к существующему заказу при повторном сканировании QR
- Улучшенный пользовательский опыт с плавными переходами между статусами

## Architecture

### High-Level Flow

```
QR Code Scan
     ↓
GET /v1/pay (process_payment_flow)
     ↓
Validation Chain
     ↓
Check Order Existence
     ├─ Order exists & valid → Redirect to /v1/order-status-page?order_id=X
     └─ Order doesn't exist → Create new order → Redirect to /v1/order-status-page?order_id=X
     ↓
Unified Order Status Page
     ├─ Status: created → Show "Перейти к оплате" button
     ├─ Status: pending → Show loading spinner + polling
     ├─ Status: paid → Show success + polling
     ├─ Status: make_pending → Show loading spinner + polling
     ├─ Status: successful → Show success (terminal)
     └─ Status: not_paid → Show error + "Повторить оплату" button
```

### Component Interaction

```
┌─────────────────────────────────────────────────────────────┐
│                    process_payment_flow()                    │
│  - Validate parameters                                       │
│  - Execute validation chain                                  │
│  - Check order existence (NEW)                               │
│  - Create order if needed                                    │
│  - Redirect to unified status page (CHANGED)                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              show_order_status_page() (ENHANCED)             │
│  - Render unified template                                   │
│  - Pass order_id to client                                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│         order_status_page.html (ENHANCED TEMPLATE)           │
│  - Fetch order data via API                                  │
│  - Render UI based on status                                 │
│  - Handle "Перейти к оплате" button (status=created)         │
│  - Handle "Повторить оплату" button (status=not_paid)        │
│  - Poll for status updates (non-terminal statuses)           │
│  - Check expiration on client side                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              GET /v1/order-status/<order_id>                 │
│                  (ENHANCED API)                              │
│  - Return order data including expires_at                    │
│  - Return device branding info                               │
│  - Return status-specific client info                        │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Backend Components

#### 1.1 Modified View: `process_payment_flow()`

**Changes:**
- Remove call to `show_order_info()` for Yookassa/TBank scenarios
- Always redirect to unified status page after order creation/validation
- Simplify routing logic

**New Flow:**
```python
def process_payment_flow(request):
    # ... existing validation logic ...
    
    # After validation chain and order creation/retrieval:
    # Always redirect to unified status page
    log_info(
        f"Redirecting to unified status page for Order {order.id}",
        'process_payment_flow'
    )
    return HttpResponseRedirect(f'/v1/order-status-page?order_id={order.id}')
```

#### 1.2 Enhanced API: `get_order_status()`

**Current Implementation:**
```python
def get_order_status(request, order_id):
    # Returns: order_id, status, drink_name, drink_size, price, device info
```

**Enhanced Implementation:**
```python
def get_order_status(request, order_id):
    # NEW: Add expires_at field to response
    data = {
        'order_id': order.id,
        'status': order.status,
        'drink_name': order.drink_name,
        'drink_size': SIZE_LABELS.get(order.size),
        'price': float(order.price / 100),
        'expires_at': order.expires_at.isoformat(),  # NEW: ISO 8601 format with timezone
        'device': {
            'location': order.device.location,
            'logo_url': order.device.logo_url,
            'client_info': order.device.client_info,  # NEW: For status=created
            'client_info_pending': order.device.client_info_pending,
            'client_info_paid': order.device.client_info_paid,
            'client_info_not_paid': order.device.client_info_not_paid,
            'client_info_make_pending': order.device.client_info_make_pending,
            'client_info_successful': order.device.client_info_successful,
        }
    }
    return JsonResponse(data, status=200)
```

#### 1.3 Modified View: `initiate_payment()`

**No changes required** - already handles payment initiation via POST request with order_id

#### 1.4 Removed Components

- **View:** `show_order_info()` - functionality moved to unified template
- **Template:** `order_info_screen.html` - replaced by enhanced `order_status_page.html`

### 2. Frontend Components

#### 2.1 Enhanced Template: `order_status_page.html`

**New Features:**
1. **Status-based UI rendering**
   - `created`: Show order details + "Перейти к оплате" button
   - `pending`, `paid`, `make_pending`: Show status + loading spinner + polling
   - `successful`: Show success message (terminal state)
   - `not_paid`: Show error + "Повторить оплату" button

2. **Client-side expiration check**
   - Parse `expires_at` from API response
   - Compare with current time on each polling cycle
   - Show error if order expired during viewing

3. **Payment initiation for status=created**
   - Button triggers POST to `/v1/initiate-payment`
   - Show loading state during payment creation
   - Handle errors gracefully

**Template Structure:**
```html
<div class="container">
    <!-- Logo Section (existing) -->
    <div class="logo-section">...</div>
    
    <!-- Order Information (existing) -->
    <div class="order-info">...</div>
    
    <!-- Status Section (enhanced) -->
    <div class="status-section">
        <!-- Dynamic content based on status -->
        <div id="status-created" style="display: none;">
            <button id="pay-button">Перейти к оплате</button>
        </div>
        
        <div id="status-pending" style="display: none;">
            <div class="spinner"></div>
            <p>Ожидаем оплату...</p>
        </div>
        
        <!-- ... other status states ... -->
    </div>
    
    <!-- Client Info Section (enhanced) -->
    <div class="client-info-section">
        <!-- Status-specific info from device.client_info_* -->
    </div>
    
    <!-- Expiration Warning (new) -->
    <div id="expiration-warning" style="display: none;">
        <p>Время действия заказа истекло</p>
    </div>
</div>

<script>
    // Fetch order data
    // Check expiration
    // Render UI based on status
    // Handle button clicks
    // Start polling for non-terminal statuses
</script>
```

## Data Models

### Order Model (No Changes)

Existing fields are sufficient:
- `id` (CharField, primary key)
- `status` (CharField with choices)
- `expires_at` (DateTimeField)
- `drink_name`, `size`, `price`
- `device` (ForeignKey)

### Device Model (No Changes)

Existing fields are sufficient:
- `logo_url`
- `client_info` (will be used for status=created)
- `client_info_pending`, `client_info_paid`, etc.

## Error Handling

### 1. Order Expiration

**Server-side:**
- `initiate_payment()` already checks `order.is_expired()`
- Returns error if order expired

**Client-side:**
```javascript
function checkOrderExpiration(expiresAt) {
    const now = new Date();
    const expirationDate = new Date(expiresAt);
    
    if (now > expirationDate) {
        // Show expiration warning
        // Hide payment button
        // Stop polling
        return true;
    }
    return false;
}
```

### 2. Order Not Found

**Scenario:** User manually enters invalid order_id in URL

**Handling:**
- `show_order_status_page()` already checks order existence
- Returns error page with 404 status

### 3. Payment Initiation Failure

**Scenario:** Payment creation fails (missing credentials, API error)

**Handling:**
- `initiate_payment()` returns JSON error response
- Client displays error message
- User can retry payment

### 4. Network Errors During Polling

**Handling:**
```javascript
async function fetchOrderStatus(orderId) {
    try {
        const response = await fetch(`/v1/order-status/${orderId}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Failed to fetch order status:', error);
        // Continue polling - transient network errors shouldn't stop updates
        return null;
    }
}
```

## Testing Strategy

### 1. Unit Tests

**Test File:** `coffee_payment/tests/test_unified_order_status.py`

**Test Cases:**

1. **test_process_payment_flow_redirects_to_status_page**
   - Verify that `process_payment_flow()` redirects to `/v1/order-status-page?order_id=X`
   - Test for both new and existing orders

2. **test_get_order_status_includes_expires_at**
   - Verify API response includes `expires_at` field
   - Verify ISO 8601 format with timezone

3. **test_get_order_status_includes_client_info**
   - Verify API response includes `device.client_info` for status=created

4. **test_show_order_status_page_with_valid_order**
   - Verify page renders successfully with valid order_id

5. **test_show_order_status_page_with_invalid_order**
   - Verify error page returned for non-existent order

6. **test_initiate_payment_with_expired_order**
   - Verify error returned when trying to pay for expired order

### 2. Integration Tests

**Test File:** `coffee_payment/tests/test_unified_order_status_integration.py`

**Test Cases:**

1. **test_full_flow_new_order**
   - Scan QR → Create order → Show status page → Initiate payment → Redirect to payment system

2. **test_full_flow_existing_order**
   - Scan QR with existing order UUID → Show status page for existing order

3. **test_full_flow_expired_order**
   - Scan QR with expired order UUID → Show error page

4. **test_status_page_polling**
   - Create order → Show status page → Update order status → Verify polling detects change

### 3. Manual Testing Checklist

- [ ] QR scan creates new order and shows status page
- [ ] QR scan with existing order shows status page for that order
- [ ] QR scan with expired order shows error
- [ ] "Перейти к оплате" button works for status=created
- [ ] Polling updates status in real-time
- [ ] Expiration warning appears when order expires during viewing
- [ ] "Повторить оплату" button works for status=not_paid
- [ ] Mobile responsive design (320px - 1920px)
- [ ] All status-specific client info displays correctly

## Migration Plan

### Phase 1: Enhance Existing Components

1. Modify `get_order_status()` to include `expires_at` and `client_info`
2. Enhance `order_status_page.html` template:
   - Add UI for status=created with payment button
   - Add client-side expiration check
   - Add payment initiation logic

### Phase 2: Update Payment Flow

1. Modify `process_payment_flow()`:
   - Remove `show_order_info()` call
   - Always redirect to unified status page

### Phase 3: Cleanup

1. Remove `show_order_info()` view function
2. Delete `order_info_screen.html` template
3. Update URL routing if needed

### Phase 4: Documentation

1. Update `PROJECT.md` with new architecture
2. Update API documentation
3. Update deployment notes

## Performance Considerations

### 1. Polling Frequency

**Current:** 1 second interval for non-terminal statuses

**Recommendation:** Keep current frequency
- Fast enough for good UX
- Low server load (simple DB query)
- Stops automatically for terminal statuses

### 2. Database Queries

**Optimization:** Use `select_related('device')` in all queries
- Already implemented in `get_order_status()`
- Reduces N+1 query problem

### 3. Client-Side Caching

**Not recommended** - Order status changes frequently, caching would cause stale data

## Security Considerations

### 1. Order ID Exposure

**Risk:** Order IDs are visible in URLs

**Mitigation:**
- Order IDs are UUIDs (hard to guess)
- No sensitive data exposed in order details
- Acceptable risk for MVP

### 2. CSRF Protection

**Current:** `@csrf_exempt` on `initiate_payment()`

**Recommendation:** Keep for MVP, consider adding CSRF tokens in future

### 3. Rate Limiting

**Not implemented** - Consider adding rate limiting for polling endpoint in production

## Accessibility

### 1. Screen Reader Support

- Use semantic HTML (`<button>`, `<section>`, etc.)
- Add ARIA labels for status indicators
- Announce status changes dynamically

### 2. Keyboard Navigation

- Ensure all buttons are keyboard accessible
- Add focus indicators

### 3. High Contrast Mode

- Already supported via CSS media queries in existing templates
- Maintain support in enhanced template

## Internationalization

**Current:** All text in Russian

**Future:** Consider extracting strings to translation files for multi-language support

## Monitoring and Logging

### Key Metrics to Track

1. **Order Creation Rate**
   - New orders vs. existing orders accessed

2. **Expiration Rate**
   - How many orders expire before payment

3. **Payment Initiation Success Rate**
   - Success vs. failure rate for payment creation

4. **Polling Performance**
   - Average response time for `/v1/order-status/<id>`

### Logging Points

All logging already implemented:
- Order creation/retrieval
- Payment initiation
- Status updates
- Error conditions

## Future Enhancements

1. **WebSocket Support**
   - Replace polling with WebSocket for real-time updates
   - Reduce server load

2. **Order History**
   - Allow users to view past orders
   - Requires user authentication

3. **Push Notifications**
   - Notify users when order status changes
   - Requires mobile app or PWA

4. **Analytics Dashboard**
   - Track order flow metrics
   - Identify bottlenecks

## Dependencies

### Backend
- Django 5.1.4 (existing)
- No new dependencies required

### Frontend
- Vanilla JavaScript (existing)
- No new dependencies required

## Rollback Plan

If issues arise after deployment:

1. **Immediate Rollback:**
   - Restore `show_order_info()` view
   - Restore `order_info_screen.html` template
   - Revert `process_payment_flow()` routing logic

2. **Data Integrity:**
   - No database migrations required
   - No data loss risk

3. **Testing Before Rollback:**
   - Verify specific issue
   - Check logs for error patterns
   - Consider hotfix instead of full rollback
