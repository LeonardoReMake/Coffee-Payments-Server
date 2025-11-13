# Implementation Plan

- [x] 1. Add client_error_info field to Device model
  - Create a new migration file to add the client_error_info TextField to the Device model
  - Set field properties: null=True, blank=True, with appropriate help_text
  - Run the migration to update the database schema
  - _Requirements: 2.1_

- [x] 2. Update render_error_page function
  - Modify the render_error_page function signature to accept an optional device parameter
  - Extract logo_url and client_error_info from device object when provided
  - Pass these values to the template context
  - Ensure backward compatibility when device parameter is not provided
  - Add logging for error page renders with device information
  - _Requirements: 3.1, 3.2_

- [x] 3. Redesign error_page.html template
- [x] 3.1 Create base HTML structure with responsive meta tags
  - Set up HTML5 doctype and head section with proper viewport meta tag
  - Add Russian language attribute to html tag
  - Create container structure matching order_info_screen.html layout
  - _Requirements: 1.3, 1.4, 4.4_

- [x] 3.2 Implement inline CSS styles with mobile-first approach
  - Copy and adapt base styles from order_info_screen.html (reset, body, container)
  - Create logo section styles with responsive sizing (120px/150px/180px)
  - Design error message section with warning colors and proper typography
  - Create client error info box styles with warning/info styling
  - Add responsive breakpoints for tablet (768px) and desktop (1024px)
  - Include accessibility media queries (high contrast, reduced motion)
  - _Requirements: 1.3, 1.4, 3.3, 3.4, 4.1_

- [x] 3.3 Implement template content sections
  - Add conditional logo section that displays when logo_url is provided
  - Create error message section with warning icon and error text
  - Add conditional client error info section that displays when client_error_info is provided
  - Implement graceful handling of missing/null values using Django template conditionals
  - Add onerror handler for logo image to handle broken URLs
  - _Requirements: 1.1, 1.5, 2.2, 2.3, 2.4, 2.5, 4.2, 4.5_

- [x] 4. Update error calls in process_payment_flow
  - Identify all render_error_page calls in views.py
  - Update calls that occur after device object is retrieved to pass device parameter
  - Ensure early validation errors (before device retrieval) continue to work without device
  - Verify all error messages reference ERROR_MESSAGES dictionary
  - _Requirements: 3.1, 3.5_

- [ ]* 5. Write tests for error screen functionality
- [ ]* 5.1 Create unit tests for Device model
  - Test that client_error_info field exists and accepts text values
  - Test that field is optional (can be null/blank)
  - Test that field can store multi-line text
  - _Requirements: 2.1_

- [ ]* 5.2 Create unit tests for render_error_page function
  - Test function with device parameter (logo and info present)
  - Test function with device parameter (only logo present)
  - Test function with device parameter (only info present)
  - Test function without device parameter (backward compatibility)
  - Test function with None values for logo_url and client_error_info
  - Verify correct context values are passed to template
  - Verify correct HTTP status codes are set
  - _Requirements: 3.5, 4.5_

- [ ]* 5.3 Create integration tests for error screen rendering
  - Test error page renders with merchant logo displayed
  - Test error page renders with client error info displayed
  - Test error page renders without optional fields
  - Test error message is displayed correctly from ERROR_MESSAGES
  - Test HTTP status code is set correctly in response
  - Test error flow in process_payment_flow with device branding
  - _Requirements: 1.1, 1.2, 1.5, 2.2, 2.5_

- [x] 6. Update PROJECT.md documentation
  - Add section describing the error screen enhancement feature
  - Document the new client_error_info field in Device model
  - Update the error handling section with new render_error_page signature
  - Add information about error screen visual design and branding
  - _Requirements: 3.2_
