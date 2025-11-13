import requests
from django.conf import settings
from django.utils import timezone
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

    def get_device_heartbeat(self, device_id: str) -> Dict[str, Any]:
        """
        Get last heartbeat for a device from Tmetr API.
        
        Args:
            device_id: UUID of the device
            
        Returns:
            API response containing heartbeat data:
            {
                'content': [
                    {
                        'deviceId': str,
                        'deviceIotName': str,
                        'heartbeatCreatedAt': int  # Unix timestamp in server timezone
                    }
                ],
                'totalElements': int,
                'offset': int,
                'limit': int
            }
            
        Raises:
            requests.RequestException: If API request fails
        """
        url = f'https://{self.host}/api/ui/v1/stat/heartbeat/recent'
        
        # Calculate timezone offset in hours
        # Get current timezone offset from Django settings
        now = timezone.now()
        offset_seconds = now.utcoffset().total_seconds() if now.utcoffset() else 0
        offset_hours = int(offset_seconds / 3600)
        
        # Create headers with X-TimeZoneOffset
        headers = self.headers.copy()
        headers['X-TimeZoneOffset'] = str(offset_hours)
        
        payload = {
            "deviceIds": [device_id],
            "offset": 0,
            "limit": 1
        }
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        return response.json()
