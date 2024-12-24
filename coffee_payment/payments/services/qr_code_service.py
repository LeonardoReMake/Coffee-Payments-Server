from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from payments.models import Device, Merchant
from datetime import datetime

def validate_device(device_uuid):
    # Попытка получить объект устройства по device_uuid
    device = get_object_or_404(Device, device_uuid=device_uuid)
    return device

def validate_merchant(device):
    # Получаем продавца по id устройства
    merchant = get_object_or_404(Merchant, id=device.merchant_id)
    # Проверяем, не истекли ли права продавца
    if hasattr(merchant, 'valid_until') and merchant.valid_until <= datetime.now().date():
        raise ValueError("Merchant permissions expired")
    return merchant

def get_redirect_url(device, query_params):
    redirect_url = device.redirect_url if hasattr(device, 'redirect_url') and device.redirect_url else "https://default-url.experttm.ru/v1/tbank-pay"
    return f"{redirect_url}?{query_params}"