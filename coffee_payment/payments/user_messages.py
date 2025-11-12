"""
Centralized user-facing messages for the payment system.
All messages shown to end users should be defined here.
"""

ERROR_MESSAGES = {
    'order_not_found': 'Заказ не найден. Пожалуйста, отсканируйте QR-код снова.',
    'order_expired': 'Время заказа истекло. Пожалуйста, создайте новый заказ.',
    'payment_creation_failed': 'Не удалось создать платеж. Пожалуйста, попробуйте позже.',
    'service_unavailable': 'Сервис временно недоступен. Пожалуйста, попробуйте позже.',
    'invalid_request': 'Некорректный запрос. Пожалуйста, попробуйте снова.',
    'missing_credentials': 'Платежная система не настроена. Обратитесь к администратору.',
    'missing_order_id': 'Отсутствует идентификатор заказа. Пожалуйста, попробуйте снова.',
}

INFO_MESSAGES = {
    'loading_payment': 'Создание платежа...',
    'redirecting': 'Перенаправление на страницу оплаты...',
}
