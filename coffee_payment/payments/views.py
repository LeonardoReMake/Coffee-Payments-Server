import json
import requests
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from payments.models import Device, Order, Drink
from payments.services.qr_code_service import validate_device, validate_merchant, get_redirect_url
from payments.utils.logging import log_error, log_info
from payments.services.telemetry_service import get_drink_price
from payments.services.yookassa_service import create_payment
from django.views.decorators.csrf import csrf_exempt
from payments.services.tmetr_service import TmetrService

# Example: GET /v1/pay?deviceUuid=test&drinkNo=9b900a2e63042d350f45b6675ef26ced&size=1&random=waxoqk&ts=1742198482&salt=b6c2cca0340a82d0dc843243299800d7&drinkName=Молочная пена&uuid=20250317110122659ba6d7-9ace-cndn
def qr_code_redirect(request):
    device_uuid = request.GET.get('deviceUuid')

    if not device_uuid:
        log_error('Missing deviceUUID parameter', 'qr_code_redirect', 'ERROR')
        return render_error_page('Missing deviceUUID parameter', 400)

    try:
        # Проверяем существование устройства
        device = validate_device(device_uuid)
        # Проверяем права продавца
        validate_merchant(device)
        # Формируем URL редиректа
        query_params = request.GET.urlencode()
        final_url = get_redirect_url(device, query_params)
        log_info(f"Redirecting to: {final_url}", 'qr_code_redirect')
        return HttpResponseRedirect(final_url)
    except Http404 as e:
        # Если устройство не найдено, возвращаем ошибку 404
        log_error(str(e), 'qr_code_redirect', 'ERROR')
        return render_error_page('Device not found', 404)
    except ValueError as e:
        # В случае истекших прав продавца возвращаем 403
        log_error(str(e), 'qr_code_redirect', 'FORBIDDEN')
        return render_error_page(str(e), 403)
    except Exception as e:
        # Для других ошибок возвращаем 500
        log_error(str(e), 'qr_code_redirect', 'ERROR')
        return render_error_page('An unexpected error occurred', 500)

def render_error_page(message, status_code):
    """
    Renders an error page with the given message and HTTP status code.
    """
    context = {'error_message': message, 'status_code': status_code}
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


# GET /v1/yook-pay?deviceUuid=test&drinkName=americano&size=1&price=10100&drinkNo=cmdrinkid&uuid=[orderUUID]
@csrf_exempt
def yookassa_payment_process(request):
    drink_price = int(5000) # фиксированная цена 50 рублей
    drink_name = request.GET.get('drinkName')
    drink_number = request.GET.get('drinkNo')
    order_uuid = request.GET.get('uuid')
    drink_size = request.GET.get('size')
    device_uuid = request.GET.get('deviceUuid')

    # TODO: получить цену напитка /api/ui/v1/static/drink
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
        log_error(f'API request failed: {str(e)}', 'yookassa_payment_process', 'ERROR')
        return render_error_page('Service temporarily unavailable', 503)
    except Exception as e:
        log_error(f'Error while getting drink information: {str(e)}', 'yookassa_payment_process', 'ERROR')
        return render_error_page('Device not found', 404)

    # Correct way to check dictionary key and value
    drink_price = drink_details.get('price', 5000) if drink_details is not None else 5000
    if drink_price == 0:
        drink_price = 5000
    log_info(f"Current price for drink {drink_price}", 'yookassa_payment_process')
    
    log_info(f"Starting yookassa process", 'yookassa_payment_process')
    
    # Get device and merchant first
    device = get_object_or_404(Device, device_uuid=device_uuid)
    merchant = device.merchant
    size_mapping = {
        '0': 1,
        '1': 2,
        '2': 3
    }
    drink_size_int = size_mapping.get(drink_size, 1)
    
    # Create order with 'created' status first
    order = Order.objects.create(
        drink_name=drink_name,
        device=device,
        merchant=merchant,
        size=drink_size_int,
        price=drink_price,
        status='created'
    )
    log_info(f"Order {order.id} created with status 'created'. Payment scenario: {device.payment_scenario}", 'yookassa_payment_process')
    
    # Check payment scenario and conditionally show order info screen
    if device.payment_scenario in ['Yookassa', 'TBank']:
        # For Yookassa and TBank: show order info screen
        log_info(f"Showing order info screen for Order {order.id} with scenario {device.payment_scenario}", 'yookassa_payment_process')
        return show_order_info(request, device, order, drink_details)
    else:
        # For Custom scenario: execute payment scenario immediately
        log_info(f"Executing payment scenario immediately for Order {order.id} with scenario {device.payment_scenario}", 'yookassa_payment_process')
        try:
            from payments.services.payment_scenario_service import PaymentScenarioService
            return PaymentScenarioService.execute_scenario(device, order, drink_details)
        except ValueError as e:
            # Missing credentials or redirect_url
            order.status = 'failed'
            order.save()
            log_error(f"Failed to execute payment scenario for order {order.id}: {str(e)}. Scenario: {device.payment_scenario}, Merchant: {merchant.id}", 'yookassa_payment_process', 'ERROR')
            return render_error_page(str(e), 400)
        except Exception as e:
            # Other errors during payment processing
            order.status = 'failed'
            order.save()
            log_error(f"Failed to process payment for order {order.id}: {str(e)}. Scenario: {device.payment_scenario}, Merchant: {merchant.id}", 'yookassa_payment_process', 'ERROR')
            return render_error_page('Service temporarily unavailable', 503)

@csrf_exempt
def yookassa_payment_result_webhook(request):
    log_info('Processing Yookassa webhook', 'django')
    log_info('Processing Yookassa webhook', 'yookassa_payment_result_webhook')
    event_json = json.loads(request.body)

    event_type = event_json['event']
    payment_id = event_json['object']['id']
    
    try:
        # Найти объект Order по external_order_id
        order = Order.objects.get(external_order_id=payment_id)
        
        # Subtask 5.1: Проверка протухания заказа
        if order.is_expired():
            log_error(f"Order {order.id} has expired", 'yookassa_payment_result_webhook', 'ERROR')
            return HttpResponse(status=400)
        
        # Subtask 5.2: Обработка успешной оплаты
        if event_type == 'payment.succeeded':
            old_status = order.status
            order.status = 'paid'
            order.save()
            log_info(f"Order {order.id} status changed: {old_status} → paid", 'yookassa_payment_result_webhook')
        
        # Subtask 5.3: Обработка неуспешной оплаты
        elif event_type == 'payment.canceled':
            old_status = order.status
            order.status = 'not_paid'
            order.save()
            log_info(f"Order {order.id} status changed: {old_status} → not_paid", 'yookassa_payment_result_webhook')
            return HttpResponse(status=200)
        
    except Order.DoesNotExist:
        log_error(f"Order with external_order_id {payment_id} not found", 'django', 'ERROR')
        return HttpResponse(status=404)
    except Exception as e:
        log_error(f"Error updating order status: {str(e)}", 'yookassa_payment_result_webhook', 'ERROR')
        return HttpResponse(status=500)

    # Только для успешных платежей продолжаем отправку команды в Tmetr API
    if event_type == 'payment.succeeded':
        #TODO: получить для устройства конфигурацию для подключения до mqtt и отправить сообщение для приготовления
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
            # Subtask 5.4: Обновление статуса после отправки команды в Tmetr API
            tmetr_service.send_make_command(
                device_id=device.device_uuid, 
                order_uuid=order_uuid, 
                drink_uuid=drink_number, 
                size=drink_size_dict[drink_size], 
                price=drink_price
            )
            old_status = order.status
            order.status = 'make_pending'
            order.save()
            log_info(f"Order {order.id} status changed: {old_status} → make_pending. Request params: device_id={device.device_uuid}, order_uuid={order_uuid}, drink_uuid={drink_number}, size={drink_size_dict[drink_size]}, price={drink_price}", 'yookassa_payment_result_webhook')
        except requests.RequestException as e:
            # Subtask 5.5: Обработка ошибок Tmetr API
            order.status = 'failed'
            order.save()
            log_error(f"Failed to send make command for order {order.id}: {str(e)}", 'yookassa_payment_result_webhook', 'ERROR')
            return HttpResponse(status=503)
        except Exception as e:
            # Subtask 5.5: Обработка ошибок Tmetr API
            order.status = 'failed'
            order.save()
            log_error(f"Failed to send make command for order {order.id}: {str(e)}", 'yookassa_payment_result_webhook', 'ERROR')
            return HttpResponse(status=503)

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
    
def show_order_info(request, device, order, drink_details):
    """
    Render the order information screen before payment initiation.
    
    Args:
        request: HttpRequest object
        device: Device instance
        order: Order instance (status='created')
        drink_details: Dict with drink information from Tmetr API
    
    Returns:
        HttpResponse with rendered order_info_screen.html template
    """
    # Size mapping from database format (1,2,3) to Russian labels
    SIZE_LABELS = {
        1: 'маленький',
        2: 'средний',
        3: 'большой'
    }
    
    # Extract drink information from drink_details
    drink_name = drink_details.get('name', order.drink_name) if drink_details else order.drink_name
    
    # Map drink size to Russian label
    drink_size_label = SIZE_LABELS.get(order.size, 'неизвестный размер')
    
    # Format price from kopecks to rubles
    drink_price_rubles = order.price / 100
    
    # Prepare context dictionary
    context = {
        'device': device,
        'order': order,
        'drink_name': drink_name,
        'drink_size': drink_size_label,
        'drink_price': drink_price_rubles,
        'logo_url': device.logo_url,
        'location': device.location,
        'client_info': device.client_info,
        'payment_scenario': device.payment_scenario
    }
    
    # Log order info screen rendering event
    log_info(
        f"Rendering order info screen for Order {order.id}, "
        f"Device {device.device_uuid}, Scenario {device.payment_scenario}",
        'show_order_info'
    )
    
    # Render template
    return render(request, 'payments/order_info_screen.html', context)


@csrf_exempt
def initiate_payment(request):
    """
    Handle payment initiation from order info screen.
    
    Args:
        request: HttpRequest object with POST data containing order_id
    
    Returns:
        HttpResponseRedirect: Redirect to payment provider URL on success
        JsonResponse: Error response with user-friendly message on failure
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
        else:
            order_id = request.POST.get('order_id')
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
        'drink_id': 'unknown',  # We don't have this stored in Order
    }
    
    # Execute payment scenario
    try:
        log_info(
            f"Executing payment scenario for Order {order.id}. "
            f"Device: {device.device_uuid}, Scenario: {device.payment_scenario}, "
            f"Price: {order.price}, Drink: {order.drink_name}",
            'initiate_payment'
        )
        
        response = PaymentScenarioService.execute_scenario(device, order, drink_details)
        
        log_info(
            f"Payment scenario executed successfully for Order {order.id}. "
            f"Status: {order.status}",
            'initiate_payment'
        )
        
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