from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from payments.models import Device
from payments.services.qr_code_service import validate_device, validate_merchant, get_redirect_url
from payments.utils.logging import log_error, log_info
from services.telemetry_service import get_drink_price
from django.views.decorators.csrf import csrf_exempt

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