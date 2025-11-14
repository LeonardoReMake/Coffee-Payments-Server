"""
URL configuration for coffee_payment project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from payments.views import (
    process_payment, 
    process_payment_flow, 
    yookassa_payment_result_webhook, 
    initiate_payment,
    show_order_status_page,
    get_order_status
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Main payment flow endpoint - handles QR code scanning and payment scenario routing
    path('v1/pay', process_payment_flow, name='process_payment_flow'),
    
    # Legacy aliases for backward compatibility
    path('v1/tbank-pay', process_payment_flow, name='tbank_pay_legacy'),
    path('v1/yook-pay', process_payment_flow, name='yook_pay_legacy'),
    
    # Payment processing endpoints
    path('v1/process_payment/', process_payment, name='process_payment'),
    path('v1/initiate-payment', initiate_payment, name='initiate_payment'),
    
    # Webhook endpoints
    path('v1/yook-pay-webhook', yookassa_payment_result_webhook, name='yookassa_payment_result_webhook'),
    
    # Order status page endpoints
    path('v1/order-status-page', show_order_status_page, name='order_status_page'),
    path('v1/order-status/<str:order_id>', get_order_status, name='get_order_status'),
]
