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
    log_info(f"Order {order.id} created with status 'created'", 'yookassa_payment_process')
    
    # Try to create payment
    try:
        payment = create_payment(drink_price/100, f'Оплата напитка: {drink_name}', "https://google.com", drink_number, order_uuid, drink_size)
        payment_data = json.loads(payment.json())
        
        # Update order with payment information and change status to 'pending'
        payment_id = payment_data['id']
        order.external_order_id = payment_id
        order.status = 'pending'
        order.save()
        log_info(f"Order {order.id} status updated to 'pending' with payment_id {payment_id}", 'yookassa_payment_process')
        
        payment_url = (payment_data['confirmation'])['confirmation_url']
        return HttpResponseRedirect(payment_url)
    except Exception as e:
        # If payment creation fails, update order status to 'failed'
        order.status = 'failed'
        order.save()
        log_error(f"Failed to create payment for order {order.id}: {str(e)}", 'yookassa_payment_process', 'ERROR')
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
    
def render_receipt_data(request, device, drink_name, drink_price, drink_size, company_name):
    context = {
        'device': device,
        'drink_name': drink_name,
        'drink_price': drink_price,
        'drink_size': drink_size,
        'company_name': company_name
    }
    return render(request, 'payments/receipt_data_form.html', context)