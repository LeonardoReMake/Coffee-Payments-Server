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
from payments.views import qr_code_redirect, process_payment, yookassa_payment_process, yookassa_payment_result_webhook

urlpatterns = [
    path('admin/', admin.site.urls),
    path('v1/pay', qr_code_redirect, name='qr_code_redirect'),
    path('v1/tbank-pay', qr_code_redirect, name='qr_code_redirect'),
    path('v1/process_payment/', process_payment, name='process_payment'),
    path('v1/yook-pay', yookassa_payment_process, name='yookassa_payment_process'),
    path('v1/yook-pay-webhook', yookassa_payment_result_webhook, name='yookassa_payment_result_webhook'),
]
