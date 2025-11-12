# Implementation Plan

- [x] 1. Рефакторинг qr_code_service.py
  - Удалить функцию `get_redirect_url()`, так как она больше не нужна
  - Оставить функции `validate_device()` и `validate_merchant()` без изменений для переиспользования
  - Добавить docstrings к функциям валидации с описанием параметров, возвращаемых значений и исключений
  - _Requirements: 1.2, 3.3_

- [x] 2. Переименование и рефакторинг основной view функции
  - [x] 2.1 Переименовать функцию `yookassa_payment_process` в `process_payment_flow` в файле views.py
    - Сохранить всю существующую логику функции
    - Обновить все внутренние логи с использованием нового имени функции 'process_payment_flow'
    - Добавить подробный docstring с описанием назначения, параметров, возвращаемых значений и обработки ошибок
    - _Requirements: 2.1, 2.4_

  - [x] 2.2 Интегрировать логику валидации из qr_code_redirect в process_payment_flow
    - Добавить валидацию всех обязательных параметров в начале функции (deviceUuid, drinkNo, drinkName, size, uuid)
    - Использовать функции `validate_device()` и `validate_merchant()` из qr_code_service
    - Добавить обработку исключений Http404 и ValueError с соответствующими сообщениями об ошибках
    - Логировать все входящие параметры запроса в начале функции
    - _Requirements: 1.1, 1.2, 3.1, 3.3, 4.1_

  - [x] 2.3 Улучшить обработку ошибок и логирование
    - Добавить централизованные сообщения об ошибках в user_messages.py (missing_parameters, device_not_found, merchant_expired)
    - Обновить все вызовы render_error_page для использования сообщений из ERROR_MESSAGES
    - Добавить логирование после валидации Device с указанием device_uuid и payment_scenario
    - Добавить логирование после получения информации о напитке с указанием цены и названия
    - Добавить логирование при маршрутизации с указанием выбранного сценария
    - _Requirements: 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4_

- [x] 3. Обновление URL конфигурации
  - Обновить импорт в urls.py: заменить `yookassa_payment_process` на `process_payment_flow`
  - Перенаправить URL `/v1/pay` на функцию `process_payment_flow` с именем 'process_payment_flow'
  - Создать алиас `/v1/tbank-pay` на `process_payment_flow` с именем 'tbank_pay_legacy'
  - Создать алиас `/v1/yook-pay` на `process_payment_flow` с именем 'yook_pay_legacy' для обратной совместимости
  - Добавить комментарии в urls.py для пояснения назначения каждого эндпоинта
  - _Requirements: 2.2, 2.5, 3.2_

- [x] 4. Удаление устаревшей функции qr_code_redirect
  - Удалить функцию `qr_code_redirect()` из views.py, так как её логика интегрирована в process_payment_flow
  - Убедиться, что все URL маршруты обновлены и не ссылаются на удаленную функцию
  - _Requirements: 3.2_

- [x] 5. Обновление документации PROJECT.md
  - Обновить раздел "Основные потоки данных" → "Инициирование платежа (QR-код)" с новой архитектурой
  - Обновить диаграмму взаимодействия компонентов с использованием process_payment_flow
  - Добавить описание функции process_payment_flow в раздел "API слой (Views)"
  - Удалить упоминания функции qr_code_redirect из документации
  - Обновить описание URL эндпоинтов с указанием алиасов для обратной совместимости
  - _Requirements: 2.1, 3.1_

- [x] 6. Создание unit тестов для process_payment_flow
  - [x] 6.1 Создать файл test_payment_flow.py в директории coffee_payment/tests/
    - Импортировать необходимые модули (Django test client, mock, timeout_decorator)
    - Создать базовый класс тестов с фикстурами для Device, Merchant, MerchantCredentials
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [x] 6.2 Написать тесты для успешных сценариев
    - test_process_payment_flow_yookassa_success: проверка создания Order и отображения экрана информации
    - test_process_payment_flow_tbank_success: проверка создания Order для TBank сценария
    - test_process_payment_flow_custom_success: проверка прямого редиректа для Custom сценария
    - _Requirements: 1.3, 1.4, 3.4, 3.5_

  - [x] 6.3 Написать тесты для обработки ошибок
    - test_process_payment_flow_missing_parameters: проверка HTTP 400 при отсутствии параметров
    - test_process_payment_flow_device_not_found: проверка HTTP 404 для несуществующего Device
    - test_process_payment_flow_merchant_expired: проверка HTTP 403 для истекшего Merchant
    - test_process_payment_flow_tmetr_api_failure: проверка HTTP 503 при ошибке Tmetr API
    - test_process_payment_flow_missing_credentials: проверка HTTP 503 при отсутствии credentials
    - _Requirements: 1.5, 5.1, 5.2, 5.3, 5.4_

  - [ ]* 6.4 Написать тесты для логирования
    - Проверить, что логируются все входящие параметры запроса
    - Проверить, что логируется выбранный payment_scenario
    - Проверить, что логируется создание Order с ID и статусом
    - Проверить, что логируются ошибки с полным контекстом
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ]* 7. Создание unit тестов для qr_code_service
  - [ ]* 7.1 Создать файл test_qr_code_service.py в директории coffee_payment/tests/
    - test_validate_device_success: проверка успешной валидации Device
    - test_validate_device_not_found: проверка выброса Http404
    - test_validate_merchant_success: проверка успешной валидации Merchant
    - test_validate_merchant_expired: проверка выброса ValueError для истекшего Merchant
    - _Requirements: 1.2, 5.2, 5.3_

- [ ]* 8. Создание integration тестов
  - [ ]* 8.1 Создать файл test_payment_flow_integration.py в директории coffee_payment/tests/
    - test_full_payment_flow_yookassa: end-to-end тест от QR-кода до webhook с проверкой всех статусов Order
    - test_full_payment_flow_custom: end-to-end тест для Custom сценария с проверкой параметров редиректа
    - Использовать моки для внешних API (Tmetr, Yookassa, TBank)
    - Добавить timeout 30 секунд для всех тестов
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 3.1, 3.4, 3.5_
