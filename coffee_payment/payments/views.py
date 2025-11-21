import json
import requests
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from payments.models import Device, Order, Drink
from payments.services.qr_code_service import validate_device, validate_merchant
from payments.utils.logging import log_error, log_info
from payments.services.telemetry_service import get_drink_price
from payments.services.yookassa_service import create_payment
from django.views.decorators.csrf import csrf_exempt
from payments.services.tmetr_service import TmetrService

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
    # Log error page render with device information
    log_error(
        f"Error page displayed: {message}. Device: {device.device_uuid if device else 'N/A'}",
        'render_error_page',
        'ERROR'
    )
    
    context = {
        'error_message': message,
        'status_code': status_code,
        'logo_url': device.logo_url if device else None,
        'client_error_info': device.client_error_info if device else None,
    }
    return render(None, 'payments/error_page.html', context, status=status_code)

def tbank_payment_proccessign(request):
    device_uuid = request.GET.get('deviceUUID')
    drink_name = request.GET.get('drinkName')
    # drink_price = request.GET.get('drinkPrice')
    drink_size = request.GET.get('size')

    if not device_uuid:
        log_error('Missing deviceUUID parameter', 'tbank_payment_proccessign', 'ERROR')
        return render_error_page('Missing deviceUUID parameter', 400)

    # Преобразование переменной drink_size
    size_mapping = {
        '0': 'маленький',
        '1': 'средний',
        '2': 'большой'
    }
    drink_size = size_mapping.get(drink_size, 'неизвестный размер')

    try:
        # Проверяем существование устройства
        device = get_object_or_404(Device, uuid=device_uuid)
        # Дополнительная логика обработки платежа
        return render_receipt_data(request, device, drink_name, get_drink_price, drink_size, device.merchant.name)
    except Http404 as e:
        # Если устройство не найдено, возвращаем ошибку 404
        log_error(str(e), 'tbank_payment_proccessign', 'ERROR')
        return render_error_page('Device not found', 404)


# GET /v1/pay?deviceUuid=test&drinkName=americano&size=1&price=10100&drinkNo=cmdrinkid&uuid=[orderUUID]
@csrf_exempt
def process_payment_flow(request):
    """
    Main payment flow handler for QR code scans from coffee machines.
    
    This function processes payment requests initiated by scanning QR codes on coffee machines.
    It handles all payment scenarios (Yookassa, TBank, Custom) by:
    1. Validating all required parameters
    2. Validating device and merchant permissions
    3. Retrieving drink information from Tmetr API
    4. Creating an order with 'created' status
    5. Routing to appropriate payment handler based on device payment scenario
    
    Args:
        request (HttpRequest): Django HTTP request object containing GET parameters:
            - deviceUuid (str, required): UUID of the coffee machine device
            - drinkName (str, required): Name of the drink
            - drinkNo (str, required): Drink ID at the device
            - size (str, required): Drink size ('0'=small, '1'=medium, '2'=large)
            - uuid (str, required): Order UUID
    
    Returns:
        HttpResponse: One of the following:
            - Rendered order info screen (for Yookassa/TBank scenarios)
            - HttpResponseRedirect to payment page (for Custom scenario)
            - Error page with appropriate HTTP status code
    
    Raises:
        Http404: If device is not found
        ValueError: If merchant permissions have expired
        requests.RequestException: If Tmetr API request fails
    
    Error Handling:
        - 400: Missing required parameters
        - 404: Device not found
        - 403: Merchant permissions expired
        - 503: Service unavailable (Tmetr API failure, missing credentials)
        - 500: Unexpected errors
    """
    from payments.user_messages import ERROR_MESSAGES
    
    # Extract all request parameters
    drink_name = request.GET.get('drinkName')
    drink_number = request.GET.get('drinkNo')
    order_uuid = request.GET.get('uuid')
    drink_size = request.GET.get('size')
    device_uuid = request.GET.get('deviceUuid')
    
    # Log all incoming request parameters
    log_info(
        f"Starting payment flow. Request params: deviceUuid={device_uuid}, "
        f"drinkNo={drink_number}, drinkName={drink_name}, size={drink_size}, uuid={order_uuid}",
        'process_payment_flow'
    )
    
    # Validate all required parameters
    if not all([device_uuid, drink_name, drink_number, order_uuid, drink_size]):
        log_error('Missing required parameters', 'process_payment_flow', 'ERROR')
        return render_error_page(ERROR_MESSAGES['missing_parameters'], 400)
    
    # Validate order ID is not empty and within length limits
    if not order_uuid.strip():
        log_error(
            f'Empty order ID provided. Raw value: "{order_uuid}", length: {len(order_uuid)}',
            'process_payment_flow',
            'ERROR'
        )
        return render_error_page(ERROR_MESSAGES['invalid_order_id'], 400)
    
    if len(order_uuid) > 255:
        log_error(
            f'Order ID exceeds maximum length: {len(order_uuid)} characters. '
            f'Order ID format: {order_uuid[:50]}... (truncated)',
            'process_payment_flow',
            'ERROR'
        )
        return render_error_page(ERROR_MESSAGES['invalid_order_id'], 400)
    
    # Execute validation chain
    from payments.services.validation_service import OrderValidationService
    
    # Prepare request parameters dictionary for validation
    request_params = {
        'deviceUuid': device_uuid,
        'drinkName': drink_name,
        'drinkNo': drink_number,
        'uuid': order_uuid,
        'size': drink_size
    }
    
    log_info(
        f"Executing validation chain for order {order_uuid}",
        'process_payment_flow'
    )
    
    # Execute validation chain with early termination on failure
    validation_result = OrderValidationService.execute_validation_chain(
        request_params=request_params,
        device_uuid=device_uuid,
        order_id=order_uuid
    )
    
    # Validate device and merchant using qr_code_service functions
    try:
        device = validate_device(device_uuid)

        is_test_device = device.status == 'test'

        # Handle validation failure
        if not validation_result['valid'] and not is_test_device:
            log_error(
                f"Validation chain failed for order {order_uuid}: {validation_result['error_message']}",
                'process_payment_flow',
                'ERROR'
            )
            return render_error_page(validation_result['error_message'], 400, device=device)
        
        # Log validation chain results
        log_info(
            f"Validation chain completed. valid={validation_result['valid']}, "
            f"should_create_new_order={validation_result['should_create_new_order']}, "
            f"error_message={validation_result['error_message']}, "
            f"is_test_device={is_test_device}",
            'process_payment_flow'
        )

        validate_merchant(device)
        
        # Log after successful device validation
        log_info(
            f"Device validated: {device.device_uuid}, payment_scenario={device.payment_scenario}",
            'process_payment_flow'
        )
    except Http404 as e:
        log_error(f'Device not found: {device_uuid}', 'process_payment_flow', 'ERROR')
        return render_error_page(ERROR_MESSAGES['device_not_found'], 404, device=None)
    except ValueError as e:
        log_error(f'Merchant validation failed: {str(e)}', 'process_payment_flow', 'FORBIDDEN')
        # Device exists but merchant validation failed, so we can pass device for branding
        return render_error_page(ERROR_MESSAGES['merchant_expired'], 403, device=device)

    # Get drink information from Tmetr API
    tmetr_service = TmetrService()
    drink_size_dict = {
        '0': 'SMALL',
        '1': 'MEDIUM',
        '2': 'BIG'
    }
    drink_details = None
    try:
        drink_details = tmetr_service.send_static_drink(
            device_id=device_uuid, 
            drink_id_at_device=drink_number, 
            drink_size=drink_size_dict[drink_size]
        )
    except requests.RequestException as e:
        log_error(f'Tmetr API request failed: {str(e)}', 'process_payment_flow', 'ERROR')
        return render_error_page(ERROR_MESSAGES['service_unavailable'], 503, device=device)
    except Exception as e:
        log_error(f'Error while getting drink information: {str(e)}', 'process_payment_flow', 'ERROR')
        return render_error_page(ERROR_MESSAGES['service_unavailable'], 503, device=device)

    # Extract drink price from API response
    drink_price = drink_details.get('price', 5000) if drink_details is not None else 5000
    if drink_price == 0:
        drink_price = 5000
    
    # Log after getting drink information
    log_info(
        f"Drink details retrieved: price={drink_price}, name={drink_name}",
        'process_payment_flow'
    )
    
    # Get merchant from device
    merchant = device.merchant
    
    # Map drink size from string to integer
    size_mapping = {
        '0': 1,
        '1': 2,
        '2': 3
    }
    drink_size_int = size_mapping.get(drink_size, 1)
    
    # Conditional order creation based on validation results
    if validation_result['should_create_new_order']:
        # Create new order with machine-generated ID from QR parameters
        from django.db import IntegrityError
        try:
            order = Order.objects.create(
                id=order_uuid,
                drink_name=drink_name,
                drink_number=drink_number,
                device=device,
                merchant=merchant,
                size=drink_size_int,
                price=drink_price,
                status='created'
            )
            log_info(
                f"Order {order.id} created with status 'created'. "
                f"Payment scenario: {device.payment_scenario}",
                'process_payment_flow'
            )
        except IntegrityError as e:
            log_error(
                f'Failed to create order with ID {order_uuid}: {str(e)}. '
                f'Order ID format: length={len(order_uuid)}, value={order_uuid[:100]}',
                'process_payment_flow',
                'ERROR'
            )
            return render_error_page(ERROR_MESSAGES['invalid_order_id'], 400, device=device)
    else:
        # Use existing valid order from validation chain
        order = validation_result['existing_order']
        log_info(
            f"Using existing order {order.id} with status '{order.status}'. "
            f"Payment scenario: {device.payment_scenario}",
            'process_payment_flow'
        )
    
    # Log routing decision
    log_info(
        f"Routing to unified status page for Order {order.id}, scenario: {device.payment_scenario}",
        'process_payment_flow'
    )
    
    # Check payment scenario and route accordingly
    if device.payment_scenario in ['Yookassa', 'YookassaReceipt', 'TBank']:
        # For Yookassa, YookassaReceipt and TBank: redirect to unified status page
        log_info(
            f"Redirecting to unified status page for Order {order.id} with scenario {device.payment_scenario}",
            'process_payment_flow'
        )
        return HttpResponseRedirect(f'/v1/order-status-page?order_id={order.id}')
    else:
        # For Custom scenario: execute payment scenario immediately
        log_info(f"Executing payment scenario immediately for Order {order.id} with scenario {device.payment_scenario}", 'process_payment_flow')
        try:
            from payments.services.payment_scenario_service import PaymentScenarioService
            return PaymentScenarioService.execute_scenario(device, order, drink_details)
        except ValueError as e:
            # Missing credentials or redirect_url
            order.status = 'failed'
            order.save()
            log_error(f"Failed to execute payment scenario for order {order.id}: {str(e)}. Scenario: {device.payment_scenario}, Merchant: {merchant.id}", 'process_payment_flow', 'ERROR')
            return render_error_page(ERROR_MESSAGES['missing_credentials'], 503, device=device)
        except Exception as e:
            # Other errors during payment processing
            order.status = 'failed'
            order.save()
            log_error(f"Failed to process payment for order {order.id}: {str(e)}. Scenario: {device.payment_scenario}, Merchant: {merchant.id}", 'process_payment_flow', 'ERROR')
            return render_error_page(ERROR_MESSAGES['service_unavailable'], 503, device=device)

@csrf_exempt
def yookassa_payment_result_webhook(request):
    log_info('Processing Yookassa webhook', 'django')
    log_info('Processing Yookassa webhook', 'yookassa_payment_result_webhook')
    event_json = json.loads(request.body)

    event_type = event_json['event']
    payment_id = event_json['object']['id']
    
    try:
        # Extract order_uuid from payment metadata
        order_uuid = event_json['object']['metadata']['order_uuid']
        
        # Find order by machine-generated ID (primary key)
        order = Order.objects.get(id=order_uuid)
        
        # Store payment system reference ID
        order.payment_reference_id = payment_id
        order.save(update_fields=['payment_reference_id'])
        
        # Subtask 5.1: Проверка протухания заказа
        if order.is_expired():
            log_error(f"Order {order.id} has expired", 'yookassa_payment_result_webhook', 'ERROR')
            return HttpResponse(status=400)
        
        # Subtask 5.2: Обработка успешной оплаты
        if event_type == 'payment.succeeded':
            old_status = order.status
            order.status = 'paid'
            order.save(update_fields=['status'])
            log_info(f"Order {order.id} status changed: {old_status} → paid", 'yookassa_payment_result_webhook')
        
        # Subtask 5.3: Обработка неуспешной оплаты
        elif event_type == 'payment.canceled':
            old_status = order.status
            order.status = 'not_paid'
            order.save(update_fields=['status'])
            log_info(f"Order {order.id} status changed: {old_status} → not_paid", 'yookassa_payment_result_webhook')
            return HttpResponse(status=200)
        
    except KeyError:
        log_error(f"Missing order_uuid in payment metadata for payment {payment_id}", 'yookassa_payment_result_webhook', 'ERROR')
        return HttpResponse(status=400)
    except Order.DoesNotExist:
        log_error(f"Order with id {order_uuid} not found", 'yookassa_payment_result_webhook', 'ERROR')
        return HttpResponse(status=404)
    except Exception as e:
        log_error(f"Error updating order status: {str(e)}", 'yookassa_payment_result_webhook', 'ERROR')
        return HttpResponse(status=500)

    # Только для успешных платежей продолжаем отправку команды в Tmetr API
    if event_type == 'payment.succeeded':
        drink_number = event_json['object']['metadata']['drink_number']
        order_uuid = event_json['object']['metadata']['order_uuid']
        drink_size = event_json['object']['metadata']['size']
        drink_price_str = event_json['object']['amount']['value']
        drink_price = int(float(drink_price_str)*100)
        device = order.device

        drink_size_dict = {
            '0': 'SMALL',
            '1': 'MEDIUM',
            '2': 'BIG'
        }

        log_info(f"Drink number: {drink_number}, order UUID: {order_uuid}, size {drink_size_dict[drink_size]}, price kop {drink_price},  deviceUUID: {device.device_uuid}", 'django')

        tmetr_service = TmetrService()
        try:
            # Попытка отправить команду приготовления
            tmetr_service.send_make_command(
                device_id=device.device_uuid, 
                order_uuid=order_uuid, 
                drink_uuid=drink_number, 
                size=drink_size_dict[drink_size], 
                price=drink_price
            )
            
            # Успешная отправка команды
            old_status = order.status
            order.status = 'make_pending'
            order.save(update_fields=['status'])
            log_info(
                f"Order {order.id} status changed: {old_status} → make_pending. "
                f"Request params: device_id={device.device_uuid}, order_uuid={order_uuid}, "
                f"drink_uuid={drink_number}, size={drink_size_dict[drink_size]}, price={drink_price}",
                'yookassa_payment_result_webhook'
            )
            
        except requests.RequestException as e:
            # Ошибка сети или API Tmetr
            old_status = order.status
            order.status = 'make_failed'
            order.save(update_fields=['status'])
            log_error(
                f"Failed to send make command for order {order.id}: {str(e)}. "
                f"Status changed: {old_status} → make_failed. "
                f"Request params: device_id={device.device_uuid}, order_uuid={order_uuid}, "
                f"drink_uuid={drink_number}, size={drink_size_dict[drink_size]}, price={drink_price}",
                'yookassa_payment_result_webhook',
                'ERROR'
            )
            # Возвращаем 200, чтобы платежная система не повторяла webhook
            return HttpResponse(status=200)
            
        except Exception as e:
            # Другие непредвиденные ошибки
            old_status = order.status
            order.status = 'make_failed'
            order.save(update_fields=['status'])
            log_error(
                f"Unexpected error sending make command for order {order.id}: {str(e)}. "
                f"Status changed: {old_status} → make_failed. "
                f"Request params: device_id={device.device_uuid}, order_uuid={order_uuid}, "
                f"drink_uuid={drink_number}, size={drink_size_dict[drink_size]}, price={drink_price}",
                'yookassa_payment_result_webhook',
                'ERROR'
            )
            # Возвращаем 200, чтобы платежная система не повторяла webhook
            return HttpResponse(status=200)

    return HttpResponse(status=200)



@csrf_exempt
def process_payment(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        # Process the payment using the provided email or phone
        # ...
        return HttpResponse('Payment processed successfully')
    return HttpResponse('Invalid request', status=400)


@csrf_exempt
def initiate_payment(request):
    """
    Handle payment initiation from order info screen.
    
    Args:
        request: HttpRequest object with POST data containing order_id
    
    Returns:
        JsonResponse: JSON response with redirect_url on success or error message on failure
    """
    from django.http import JsonResponse
    from payments.user_messages import ERROR_MESSAGES
    from payments.services.payment_scenario_service import PaymentScenarioService
    
    if request.method != 'POST':
        return JsonResponse(
            {'error': ERROR_MESSAGES['invalid_request']},
            status=400
        )
    
    # Parse request body for JSON data
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            order_id = data.get('order_id')
            email = data.get('email')
        else:
            order_id = request.POST.get('order_id')
            email = request.POST.get('email')
    except json.JSONDecodeError:
        log_error(
            "Failed to parse JSON request body",
            'initiate_payment',
            'ERROR'
        )
        return JsonResponse(
            {'error': ERROR_MESSAGES['invalid_request']},
            status=400
        )
    
    # Validate email format if provided
    if email:
        import re
        email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not re.match(email_pattern, email):
            log_error(
                f"Invalid email format for order {order_id}: {email}",
                'initiate_payment',
                'ERROR'
            )
            return JsonResponse(
                {'error': 'Некорректный формат email'},
                status=400
            )
    
    # Validate order_id parameter
    if not order_id:
        log_error(
            "Missing order_id parameter in payment initiation request",
            'initiate_payment',
            'ERROR'
        )
        return JsonResponse(
            {'error': ERROR_MESSAGES['missing_order_id']},
            status=400
        )
    
    # Log payment initiation attempt with all request parameters
    log_info(
        f"Payment initiation attempt for order_id={order_id}. "
        f"Request method: {request.method}, Content-Type: {request.content_type}",
        'initiate_payment'
    )
    
    # Retrieve Order instance
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        log_error(
            f"Order not found: {order_id}",
            'initiate_payment',
            'ERROR'
        )
        return JsonResponse(
            {'error': ERROR_MESSAGES['order_not_found']},
            status=404
        )
    
    # Check if order has expired
    if order.is_expired():
        log_error(
            f"Order {order.id} has expired. Expires at: {order.expires_at}",
            'initiate_payment',
            'ERROR'
        )
        return JsonResponse(
            {'error': ERROR_MESSAGES['order_expired']},
            status=400
        )
    
    # Get device and prepare drink_details for payment scenario
    device = order.device
    
    # Reconstruct drink_details from order data
    # This is needed for PaymentScenarioService.execute_scenario
    drink_details = {
        'price': int(order.price),  # Price in kopecks
        'name': order.drink_name,
        'drink_id': order.drink_number if order.drink_number else 'unknown',
    }
    
    # Execute payment scenario
    try:
        log_info(
            f"Executing payment scenario for Order {order.id}. "
            f"Device: {device.device_uuid}, Scenario: {device.payment_scenario}, "
            f"Price: {order.price}, Drink: {order.drink_name}, "
            f"Email: {'provided' if email else 'not provided'}",
            'initiate_payment'
        )
        
        # Handle YookassaReceipt scenario separately to pass email
        if device.payment_scenario == 'YookassaReceipt':
            response = PaymentScenarioService.execute_yookassa_receipt_scenario(
                device, order, drink_details, email=email
            )
        else:
            response = PaymentScenarioService.execute_scenario(device, order, drink_details)
        
        log_info(
            f"Payment scenario executed successfully for Order {order.id}. "
            f"Status: {order.status}",
            'initiate_payment'
        )
        
        # Extract redirect URL from HttpResponseRedirect and return as JSON
        if isinstance(response, HttpResponseRedirect):
            redirect_url = response.url
            return JsonResponse({'redirect_url': redirect_url}, status=200)
        else:
            # If response is not a redirect, return it as-is
            return response
        
    except ValueError as e:
        # Missing credentials or configuration error
        log_error(
            f"Payment initiation failed for Order {order.id}: {str(e)}. "
            f"Scenario: {device.payment_scenario}, Device: {device.device_uuid}",
            'initiate_payment',
            'ERROR'
        )
        return JsonResponse(
            {'error': ERROR_MESSAGES['missing_credentials']},
            status=503
        )
    except Exception as e:
        # Other errors during payment processing
        log_error(
            f"Payment creation failed for Order {order.id}: {str(e)}. "
            f"Scenario: {device.payment_scenario}, Device: {device.device_uuid}",
            'initiate_payment',
            'ERROR'
        )
        return JsonResponse(
            {'error': ERROR_MESSAGES['payment_creation_failed']},
            status=503
        )


def render_receipt_data(request, device, drink_name, drink_price, drink_size, company_name):
    context = {
        'device': device,
        'drink_name': drink_name,
        'drink_price': drink_price,
        'drink_size': drink_size,
        'company_name': company_name
    }
    return render(request, 'payments/receipt_data_form.html', context)


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
    
    # Log successful request
    log_info(
        f"Order status retrieved for order {order_id}. Status: {order.status}",
        'get_order_status'
    )
    
    # Get payment scenario and receipt config
    device = order.device
    payment_scenario = device.payment_scenario
    is_receipt_mandatory = False
    
    if payment_scenario == 'YookassaReceipt':
        try:
            from payments.models import MerchantCredentials
            credentials = MerchantCredentials.objects.get(
                merchant=device.merchant,
                scenario='YookassaReceipt'
            )
            is_receipt_mandatory = credentials.credentials.get('is_receipt_mandatory', False)
        except MerchantCredentials.DoesNotExist:
            log_info(
                f"YookassaReceipt credentials not found for merchant {device.merchant.id}, "
                f"defaulting is_receipt_mandatory to False",
                'get_order_status'
            )
    
    # Prepare response data
    data = {
        'order_id': order.id,
        'status': order.status,
        'drink_name': order.drink_name,
        'drink_size': SIZE_LABELS.get(order.size, 'неизвестный размер'),
        'price': float(order.price / 100),  # Convert kopecks to rubles
        'expires_at': order.expires_at.isoformat(),  # ISO 8601 format with timezone
        'payment_scenario': payment_scenario,
        'is_receipt_mandatory': is_receipt_mandatory,
        'device': {
            'location': order.device.location,
            'logo_url': order.device.logo_url,
            'client_info': order.device.client_info,  # For status=created
            'client_info_pending': order.device.client_info_pending,
            'client_info_paid': order.device.client_info_paid,
            'client_info_not_paid': order.device.client_info_not_paid,
            'client_info_make_pending': order.device.client_info_make_pending,
            'client_info_successful': order.device.client_info_successful,
            'client_info_make_failed': order.device.client_info_make_failed,
        }
    }
    
    return JsonResponse(data, status=200)


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
