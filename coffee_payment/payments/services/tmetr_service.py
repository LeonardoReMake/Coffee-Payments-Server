import requests
from django.conf import settings
from typing import Dict, Any, List

class TmetrService:
    def __init__(self):
        self.token = settings.TMETR_TOKEN
        self.host = settings.TMETR_HOST
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'TimeZoneOffset': '3',
            'Content-Type': 'application/json'
        }

    def send_static_drink(self, device_id: str, drink_id_at_device: str, drink_size: str) -> Dict[str, Any]:
        """
        Send static drink information to Tmetr API
        
        Args:
            device_id: UUID of the device
            drink_id_at_device: UUID of the drink at the device
            drink_size: Size of the drink (e.g., "SMALL")
            
        Returns:
            API response as dictionary
        """
        url = f'https://{self.host}/api/ui/v1/static/drink'
        
        payload = {
            "deviceId": device_id,
            "drinkIdAtDevice": drink_id_at_device,
            "drinkSize": drink_size
        }
        
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        
        return response.json()

    def send_make_command(self, device_id: str, order_uuid: str, drink_uuid: str, 
                         size: str, price: int) -> Dict[str, Any]:
        """
        Send make command to Tmetr API
        
        Args:
            device_id: UUID of the device
            order_uuid: UUID of the order
            drink_uuid: UUID of the drink
            size: Size of the drink (e.g., "small")
            price: Price of the drink
            
        Returns:
            API response as dictionary
        """
        url = f'https://{self.host}/api/commander/v1/command/make'
        
        payload = [{
            "deviceId": device_id,
            "orderUuid": order_uuid,
            "drinkUuid": drink_uuid,
            "size": size.lower(),  # Приводим к нижнему регистру для соответствия API
            "price": price
        }]
        
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        
        return response.json()
