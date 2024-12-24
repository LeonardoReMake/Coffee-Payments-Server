# tinkoff_service.py

import hashlib
import hmac
import requests
from django.conf import settings
from models import TBankPayment
from payments.utils.logging import log_error, log_info

def generate_token(data):
    """
    Формирует токен для запроса к API Т-Банка.
    """
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
    secret_key = settings.SECRET_KEY.encode('utf-8')
    sign_string = sign_string.encode('utf-8')
    token = hmac.new(secret_key, sign_string, hashlib.sha256).hexdigest().upper()
    
    log_info(f"Final token: {token}",  "t_bank_service")

    return token

def create_payment_api(data):
    """
    Отправляет запрос на создание платежа в API Т-Банка.
    """
    try:
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

def process_payment(payment_data):
    """
    Обрабатывает создание платежа и сохраняет информацию в базу данных.
    """
    # Генерация токена для подписи
    token = generate_token(payment_data)
    payment_data["Token"] = token

    # Отправка запроса в Т-Банк
    response, error = create_payment_api(payment_data)

    if response.get("Success"):
        # Сохраняем информацию о платеже в базу данных
        payment = TBankPayment.objects.create(order_id=response.get("OrderId"), amount=response.get("Amount"), payment_url=response.get("PaymentURL"), payment_id=response.get("PaymentId"), status=response.get("Status"))
        return payment, None
    else:
        return None, response
