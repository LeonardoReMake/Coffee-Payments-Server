import json
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from payments.models import Device, Order, Drink
from payments.services.qr_code_service import validate_device, validate_merchant, get_redirect_url
from payments.utils.logging import log_error, log_info
from payments.services.telemetry_service import get_drink_price
from payments.services.yookassa_service import create_payment
from django.views.decorators.csrf import csrf_exempt
from yookassa.domain.notification import WebhookNotification

def qr_code_redirect(request):
    device_uuid = request.GET.get('deviceUUID')

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


# GET /v1/yook-pay?deviceUUID=test&drinkName=americano&size=1&price=10100&drinkNo=cmdrinkid&orderUUID=cmorderuuid
@csrf_exempt
def yookassa_payment_process(request):
    drink_price = int(request.GET.get('price'))
    drink_name = request.GET.get('drinkName')
    drink_number = request.GET.get('drinkNo')
    order_uuid = request.GET.get('orderUUID')
    drink_size = request.GET.get('size')

    log_info(f"Starting yookassa process", 'yookassa_payment_process')
    payment = create_payment(drink_price/100, f'Оплата напитка: {drink_name}', "https://google.com", drink_number, order_uuid, drink_size)
    payment_data = json.loads(payment.json())

    # Создание объекта Order на основе объекта payment
    payment_id = payment_data['id']
    payment_status = payment_data['status']
    amount = int(float(payment_data['amount']['value']) * 100)  # Convert to kopecks
    status_mapping = {
        'pending': 'pending',
        'waiting_for_capture': 'pending',
        'succeeded': 'success',
        'canceled': 'failed',
    }
    status = status_mapping.get(payment_status, 'failed')
    device = get_object_or_404(Device, device_uuid=request.GET.get('deviceUUID'))
    merchant = device.merchant
    size_mapping = {
        '0': 1,
        '1': 2,
        '2': 3
    }
    drink_size = size_mapping.get(drink_size, 'неизвестный размер')

    order = Order.objects.create(
        external_order_id=payment_id,
        drink_name=drink_name,
        device=device,
        merchant=merchant,
        size=drink_size,
        price=amount,
        status=status
    )

    payment_url = (payment_data['confirmation'])['confirmation_url']
    return HttpResponseRedirect(payment_url)

@csrf_exempt
def yookassa_payment_result_webhook(request):
    log_info('Processing Yookassa webhook', 'yookassa_payment_result_webhook')
    event_json = json.loads(request.body)

    event_type = event_json['event']
    payment_id = event_json['object']['id']
    
    if (event_type == 'payment.succeeded'):
        try:
            # Найти объект Order по external_order_id
            order = Order.objects.get(external_order_id=payment_id)
            
            # Изменить статус на success
            order.status = 'success'
            order.save()
            
            log_info(f"Order {order.id} status updated to success", 'yookassa_payment_result_webhook')
        except Order.DoesNotExist:
            log_error(f"Order with external_order_id {payment_id} not found", 'yookassa_payment_result_webhook', 'ERROR')
            return HttpResponse(status=404)
        except Exception as e:
            log_error(f"Error updating order status: {str(e)}", 'yookassa_payment_result_webhook', 'ERROR')
            return HttpResponse(status=500)

    #TODO: получить для устройства конфигурацию для подключения до mqtt и отправить сообщение для приготовления
    drink_number = event_json['object']['metadata']['drink_number']
    order_uuid = event_json['object']['metadata']['order_uuid']
    drink_size = event_json['object']['metadata']['size']
    device = order.device
    log_info(f"Drink number: {drink_number}, order UUID: {order_uuid}, size {drink_size},  deviceUUID: {device.device_uuid}", 'yookassa_payment_result_webhook')
    print(f"Drink number: {drink_number}, order UUID: {order_uuid}, size {drink_size},  deviceUUID: {device.device_uuid}")

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