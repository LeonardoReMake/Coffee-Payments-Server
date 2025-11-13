# Design Document

## Overview

This design enhances the error page (`error_page.html`) to provide a modern, user-friendly experience that matches the visual design of the order information screen. The error screen will display merchant branding, clear error messages, and optional support information to help users understand and resolve issues.

The design follows the mobile-first approach and maintains consistency with the existing order information screen while adapting the layout for error scenarios.

## Architecture

### Component Structure

```
Error Screen Display Flow
├── View Layer (views.py)
│   └── render_error_page(message, status_code, device=None)
│       ├── Accepts error message from ERROR_MESSAGES
│       ├── Accepts optional Device object for branding
│       └── Renders error_page.html template
│
├── Template Layer (error_page.html)
│   ├── Logo Section (conditional)
│   ├── Error Message Section
│   ├── Client Error Info Section (conditional)
│   └── Inline CSS (mobile-first, responsive)
│
└── Data Model (models.py)
    └── Device model
        ├── logo_url (existing field)
        └── client_error_info (new field)
```

### Design Principles

1. **Visual Consistency**: Match the order information screen's color scheme, typography, and spacing
2. **Mobile First**: Optimize for 320px width, then enhance for larger screens
3. **Graceful Degradation**: Display error information even if logo or additional info is unavailable
4. **Self-Contained**: All CSS inline, no external dependencies
5. **Accessibility**: Support high contrast mode and reduced motion preferences

## Components and Interfaces

### 1. Device Model Extension

Add a new field to the Device model to store custom error screen information:

```python
class Device(models.Model):
    # ... existing fields ...
    
    client_error_info = models.TextField(
        null=True,
        blank=True,
        help_text='Custom information displayed to customers on error screens (e.g., support contact)'
    )
```

**Migration Required**: Yes, a new migration will be created to add the `client_error_info` field.

### 2. View Function Update

Modify the `render_error_page` function to accept an optional Device object:

```python
def render_error_page(message, status_code, device=None):
    """
    Renders an error page with the given message and HTTP status code.
    
    Args:
        message (str): User-friendly error message from ERROR_MESSAGES
        status_code (int): HTTP status code (400, 403, 404, 503, etc.)
        device (Device, optional): Device object for displaying merchant branding
    
    Returns:
        HttpResponse: Rendered error page
    """
    context = {
        'error_message': message,
        'status_code': status_code,
        'logo_url': device.logo_url if device else None,
        'client_error_info': device.client_error_info if device else None,
    }
    return render(None, 'payments/error_page.html', context, status=status_code)
```

**Backward Compatibility**: The function remains backward compatible - existing calls without the `device` parameter will continue to work, displaying errors without branding.

### 3. Template Design (error_page.html)

The template will follow the structure of `order_info_screen.html` with adaptations for error display:

#### Layout Structure

```
┌─────────────────────────────────┐
│                                 │
│    [Merchant Logo] (optional)   │
│                                 │
├─────────────────────────────────┤
│                                 │
│         ⚠️ Ошибка               │
│                                 │
│    [User-friendly message]      │
│                                 │
├─────────────────────────────────┤
│                                 │
│  [Client Error Info] (optional) │
│                                 │
└─────────────────────────────────┘
```

#### Visual Design Specifications

**Colors** (matching order_info_screen.html):
- Background: `#f5f5f5`
- Container: `#ffffff`
- Primary text: `#1a1a1a`
- Secondary text: `#666`
- Error accent: `#e74c3c` (red for error state)
- Info box background: `#fff3cd` (light yellow for warnings)
- Info box border: `#ffc107` (amber)

**Typography**:
- Font family: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif`
- Heading: 24px (mobile), 28px (tablet), 32px (desktop)
- Body text: 16px (mobile), 17px (tablet), 18px (desktop)
- Line height: 1.6

**Spacing**:
- Container padding: 24px (mobile), 32px (tablet), 40px (desktop)
- Section margins: 24px
- Border radius: 12px (container), 4px (info box)

**Logo Sizing**:
- Mobile: max 120px × 120px
- Tablet: max 150px × 150px
- Desktop: max 180px × 180px
- Object-fit: contain (maintain aspect ratio)

#### Responsive Breakpoints

- Mobile: 320px - 767px
- Tablet: 768px - 1023px
- Desktop: 1024px+

### 4. Error Icon

Use a Unicode warning symbol (⚠️) or HTML entity (`&#9888;`) for the error indicator. This avoids external dependencies while providing a clear visual cue.

## Data Models

### Device Model Changes

```python
class Device(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device_uuid = models.CharField(max_length=255, unique=True)
    redirect_url = models.URLField(null=True, blank=True)
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name="devices")
    location = models.CharField(max_length=255)
    status = models.CharField(max_length=50, choices=[...])
    last_interaction = models.DateTimeField()
    payment_scenario = models.CharField(max_length=50, default='Yookassa')
    logo_url = models.URLField(null=True, blank=True, help_text='...')
    client_info = models.TextField(null=True, blank=True, help_text='...')
    
    # NEW FIELD
    client_error_info = models.TextField(
        null=True,
        blank=True,
        help_text='Custom information displayed to customers on error screens (e.g., support contact)'
    )
```

**Field Properties**:
- Type: TextField (allows multi-line text)
- Nullable: Yes (optional field)
- Blank: Yes (can be empty in forms)
- Help text: Descriptive text for Django Admin

## Error Handling

### Template Error Handling

The template will gracefully handle missing or null values:

1. **Missing logo_url**: Logo section is not rendered
2. **Missing client_error_info**: Info box is not rendered
3. **Missing device object**: Only error message is displayed (backward compatible)
4. **Logo load failure**: Use `onerror` attribute to hide broken image

### View Error Handling

The view function will safely access Device attributes:

```python
logo_url = device.logo_url if device else None
client_error_info = device.client_error_info if device else None
```

This prevents AttributeError if device is None.

## Integration Points

### 1. Updating Existing Error Calls

Most error calls in `process_payment_flow` already have access to the `device` object. These calls should be updated to pass the device:

**Before**:
```python
return render_error_page(ERROR_MESSAGES['device_not_found'], 404)
```

**After**:
```python
return render_error_page(ERROR_MESSAGES['device_not_found'], 404, device=device)
```

**Exception**: Early validation errors (before device is retrieved) will continue to work without the device parameter.

### 2. Logging

All error page renders should be logged using the existing logging utility:

```python
from payments.utils.logging import log_error

log_error(
    f"Error page displayed: {message}. Device: {device.device_uuid if device else 'N/A'}",
    'render_error_page',
    'ERROR'
)
```

## Testing Strategy

### Unit Tests

1. **Test Device Model**:
   - Verify client_error_info field exists and accepts text
   - Verify field is optional (null=True, blank=True)
   - Verify field can store multi-line text

2. **Test render_error_page Function**:
   - Test with device parameter (logo and info present)
   - Test with device parameter (logo only)
   - Test with device parameter (info only)
   - Test without device parameter (backward compatibility)
   - Test with None values for logo_url and client_error_info

### Integration Tests

1. **Test Error Screen Rendering**:
   - Verify error page displays with merchant logo
   - Verify error page displays with client error info
   - Verify error page displays without optional fields
   - Verify error message is displayed correctly
   - Verify HTTP status code is set correctly

2. **Test Error Flow in process_payment_flow**:
   - Trigger various error conditions
   - Verify error page is rendered with device branding
   - Verify error messages come from ERROR_MESSAGES

### Visual/Manual Tests

1. **Responsive Design**:
   - Test on mobile (320px, 375px, 414px widths)
   - Test on tablet (768px, 1024px widths)
   - Test on desktop (1280px, 1920px widths)

2. **Visual Consistency**:
   - Compare error screen with order info screen
   - Verify colors, fonts, spacing match
   - Verify logo sizing is consistent

3. **Accessibility**:
   - Test with high contrast mode enabled
   - Test with reduced motion preference
   - Test with screen reader

4. **Edge Cases**:
   - Test with very long error messages
   - Test with very long client_error_info text
   - Test with broken logo URL
   - Test with missing logo URL

## Implementation Notes

### CSS Reuse

The error page CSS will reuse many styles from the order info screen:
- Container styles
- Logo section styles
- Typography styles
- Responsive breakpoints
- Accessibility media queries

### Differences from Order Info Screen

1. **No interactive elements**: Error screen is informational only (no buttons)
2. **Error-specific styling**: Use warning/error colors for the message section
3. **Simplified layout**: No order details table, just message and info sections
4. **Different info box styling**: Use warning colors instead of info colors

### Migration Strategy

1. Create migration to add `client_error_info` field to Device model
2. Run migration on development environment
3. Update `render_error_page` function signature
4. Update `error_page.html` template
5. Update error calls in `process_payment_flow` to pass device
6. Test all error scenarios
7. Deploy to production

### Backward Compatibility

The design maintains backward compatibility:
- Existing error calls without device parameter continue to work
- Template handles missing device gracefully
- No breaking changes to existing functionality

## Future Enhancements

1. **Localization**: Support multiple languages for error messages
2. **Error Codes**: Display user-friendly error codes for support reference
3. **Retry Actions**: Add "Try Again" button for recoverable errors
4. **Error Analytics**: Track error frequency and types for monitoring
5. **Custom Error Pages**: Allow merchants to customize error page styling
