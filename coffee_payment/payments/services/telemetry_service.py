from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from payments.models import Device, Merchant
from datetime import datetime

def get_drink_price(device_id, drink_uuid, drink_size):
    return 10000