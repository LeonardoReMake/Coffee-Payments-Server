# Requirements Document

## Introduction

Данная функциональность объединяет экран информации о заказе (`order_info_screen.html`) и страницу отслеживания статуса заказа (`order_status_page.html`) в единую универсальную страницу. Это устраняет дублирование кода и улучшает пользовательский опыт, позволяя клиентам возвращаться к существующим заказам при повторном сканировании QR-кода.

## Glossary

- **Order Status System** — система отслеживания статуса заказа в реальном времени
- **QR Code** — QR-код на кофемашине, содержащий параметры заказа
- **Order Expiration** — механизм протухания заказов по времени (expires_at)
- **Payment Flow** — процесс обработки платежа от сканирования QR до получения напитка
- **Order Info Screen** — текущий экран с информацией о заказе перед оплатой
- **Order Status Page** — текущая страница отслеживания статуса заказа
- **Unified Status Page** — новая универсальная страница, объединяющая функциональность обоих экранов
- **API Endpoint** — REST API точка доступа для получения данных о заказе
- **Polling** — периодический опрос сервера для обновления статуса заказа

## Requirements

### Requirement 1

**User Story:** Как клиент, я хочу видеть единую страницу статуса заказа после сканирования QR-кода, чтобы иметь консистентный опыт взаимодействия с системой.

#### Acceptance Criteria

1. WHEN клиент сканирует QR-код на кофемашине, THE Order Status System SHALL отображать универсальную страницу статуса заказа вместо отдельного экрана информации о заказе
2. WHEN заказ находится в статусе 'created', THE Order Status System SHALL отображать информацию о заказе с кнопкой "Перейти к оплате"
3. WHEN заказ находится в статусах 'pending', 'paid', 'make_pending', 'successful', 'not_paid', THE Order Status System SHALL отображать соответствующий статус с автоматическим обновлением
4. WHEN клиент нажимает кнопку "Перейти к оплате" для заказа в статусе 'created', THE Order Status System SHALL инициировать процесс оплаты через API
5. THE Order Status System SHALL использовать mobile-first дизайн с адаптивной версткой для разрешений от 320px до 1920px

### Requirement 2

**User Story:** Как клиент, я хочу иметь возможность вернуться к существующему заказу при повторном сканировании QR-кода, чтобы продолжить процесс оплаты или проверить статус.

#### Acceptance Criteria

1. WHEN клиент повторно сканирует QR-код с тем же UUID заказа, THE Payment Flow SHALL проверять существование заказа в базе данных
2. IF заказ существует и не протух (expires_at > текущее время), THEN THE Payment Flow SHALL перенаправлять клиента на страницу статуса существующего заказа
3. IF заказ существует но протух (expires_at <= текущее время), THEN THE Payment Flow SHALL отображать экран ошибки с сообщением о протухании заказа
4. IF заказ не существует, THEN THE Payment Flow SHALL создавать новый заказ со статусом 'created'
5. THE Payment Flow SHALL логировать все проверки существования заказа с UUID заказа и результатом проверки

### Requirement 3

**User Story:** Как клиент, я хочу видеть актуальную информацию о времени действия заказа, чтобы понимать, сколько времени у меня есть на оплату.

#### Acceptance Criteria

1. THE Order Status System SHALL добавлять поле expires_at в JSON ответ API метода получения статуса заказа
2. THE Unified Status Page SHALL отображать время протухания заказа в формате с указанием таймзоны (например, 2025-11-15T10:30:00+03:00)
3. WHEN клиент открывает страницу статуса заказа, THE Unified Status Page SHALL проверять валидность заказа по времени на клиентской стороне
4. IF заказ протух во время просмотра страницы, THEN THE Unified Status Page SHALL отображать сообщение об ошибке и блокировать возможность оплаты
5. THE Unified Status Page SHALL обновлять проверку валидности заказа при каждом polling запросе

### Requirement 4

**User Story:** Как разработчик, я хочу иметь REST API для получения полной информации о заказе, чтобы клиентская часть могла отображать актуальные данные.

#### Acceptance Criteria

1. THE Order Status System SHALL предоставлять API endpoint GET /v1/order-status/<order_id> для получения информации о заказе
2. THE API endpoint SHALL возвращать JSON с полями: id, status, drink_name, size, price, device_location, logo_url, client_info, expires_at, status_specific_info
3. THE API endpoint SHALL возвращать HTTP статус 404 если заказ не найден
4. THE API endpoint SHALL возвращать HTTP статус 200 с данными заказа если заказ найден
5. THE API endpoint SHALL логировать все запросы с order_id и результатом обработки

### Requirement 5

**User Story:** Как администратор системы, я хочу чтобы старый экран информации о заказе был удален, чтобы избежать дублирования кода и упростить поддержку.

#### Acceptance Criteria

1. THE Order Status System SHALL удалять шаблон order_info_screen.html после миграции функциональности
2. THE Order Status System SHALL удалять view функцию show_order_info() после миграции функциональности
3. THE Payment Flow SHALL использовать только Unified Status Page для всех платежных сценариев (Yookassa, TBank)
4. THE Order Status System SHALL обновлять документацию PROJECT.md с описанием новой архитектуры
5. THE Order Status System SHALL сохранять обратную совместимость с существующими URL endpoints для страницы статуса заказа
