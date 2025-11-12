# tinkoff_service.py

import hashlib
import hmac
import requests
from django.conf import settings
from payments.models import TBankPayment
from payments.utils.logging import log_error, log_info

def generate_token(data, secret_key=None):
    """
    Формирует токен для запроса к API Т-Банка.
    
    Args:
        data: Payment data dictionary
        secret_key: Optional secret key from credentials. If not provided, uses Django SECRET_KEY.
    """

    #TODO: Проверить генерацию токена
    
    # Исключаем поля 'Shops' и 'Receipt' из данных
    filtered_data = {key: value for key, value in data.items() if key not in ['Shops', 'Receipt']}
    
    log_info(f"Filtered: {filtered_data}",  "t_bank_service")

    # Сортируем данные по ключам
    sorted_data = sorted(filtered_data.items())

    log_info(f"Sorted: {sorted_data}",  "t_bank_service")
    
    # Формируем строку для подписи
    sign_string = ''.join([f"{value}" for _, value in sorted_data])

    log_info(f"Sign string: {sign_string}",  "t_bank_service")
    
    # Создаем подпись с использованием HMAC и секретного ключа
    # Use provided secret_key or fall back to Django settings
    if secret_key is None:
        secret_key = settings.SECRET_KEY
    
    secret_key_bytes = secret_key.encode('utf-8')
    sign_string_bytes = sign_string.encode('utf-8')
    token = hmac.new(secret_key_bytes, sign_string_bytes, hashlib.sha256).hexdigest().upper()
    
    log_info(f"Final token: {token}",  "t_bank_service")

    return token

def create_payment_api(data, credentials=None):
    """
    Отправляет запрос на создание платежа в API Т-Банка.
    
    Args:
        data: Payment data dictionary
        credentials: Optional dict with TBank credentials (e.g., 'base_url'). 
                    If not provided, uses settings.T_BANK_BASE_URL.
    """
    try:
        # Use provided base_url from credentials or fall back to settings
        if credentials and 'base_url' in credentials:
            t_bank_base_url = credentials['base_url']
        else:
            t_bank_base_url = settings.T_BANK_BASE_URL
        
        response = requests.post(f"{t_bank_base_url}/v2/Init", json=data)
        response_data = response.json()

        if response_data.get("Success"):
            log_info(f"Создан платеж с PaymentId: {response_data.get("PaymentId")} и OrderId: {response_data.get("OrderId")}", "t_bank_service")
            return response_data, None
        else:
            log_error(f"Ошибка при создании платежа: {response_data}", "t_bank_service")
            return response_data, f"Ошибка создания платежа"
    except Exception as e:
        log_error(f"Исключение при запросе к API Т-Банка: {e}", "t_bank_service")
        return None, "Не удалось создать платеж"

def process_payment(payment_data, credentials=None):
    """
    Обрабатывает создание платежа и сохраняет информацию в базу данных.
    
    Args:
        payment_data: Payment data dictionary
        credentials: Optional dict with TBank credentials (e.g., 'secret_key', 'base_url').
                    If not provided, uses default settings.
    """
    # Генерация токена для подписи
    # Extract secret_key from credentials if provided
    secret_key = credentials.get('secret_key') if credentials else None
    token = generate_token(payment_data, secret_key)
    payment_data["Token"] = token

    # Отправка запроса в Т-Банк
    response, error = create_payment_api(payment_data, credentials)

    if response.get("Success"):
        # Сохраняем информацию о платеже в базу данных
        payment = TBankPayment.objects.create(order_id=response.get("OrderId"), amount=response.get("Amount"), payment_url=response.get("PaymentURL"), payment_id=response.get("PaymentId"), status=response.get("Status"))
        return payment, None
    else:
        return None, response
