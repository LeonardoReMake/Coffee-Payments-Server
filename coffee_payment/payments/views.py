from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.shortcuts import render
from payments.services.qr_code_service import validate_device, validate_merchant, get_redirect_url
from payments.utils.logging import log_error, log_info

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