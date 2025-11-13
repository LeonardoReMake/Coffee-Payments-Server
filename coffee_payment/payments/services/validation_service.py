"""
Order validation service for the coffee payment system.
Provides validation chain execution with early termination on failure.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, Optional
from django.conf import settings
from django.utils import timezone

from payments.models import Order
from payments.services.tmetr_service import TmetrService
from payments.user_messages import ERROR_MESSAGES


logger = logging.getLogger(__name__)


class OrderValidationService:
    """
    Service for validating orders before payment processing.
    Executes validation chain with early termination on failure.
    """
    
    @staticmethod
    def validate_request_hash(request_params: dict) -> Tuple[bool, Optional[str]]:
        """
        Validates request hash for authenticity.
        
        This is a placeholder implementation that always returns success.
        Future implementation will verify cryptographic hash.
        
        Args:
            request_params: Dictionary containing all request parameters
            
        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if validation passes, False otherwise
            - error_message: Error message key from user_messages.py if validation fails
        """
        logger.info(
            f"[validate_request_hash] Hash validation (placeholder). "
            f"Parameters: {list(request_params.keys())}"
        )
        
        # Placeholder: always return success
        logger.info("[validate_request_hash] Hash validation passed (placeholder implementation)")
        return True, None
    
    @staticmethod
    def check_order_existence(order_id: str) -> Tuple[bool, Optional[str], Optional[Order]]:
        """
        Checks if order exists and validates its state.
        
        Args:
            order_id: Machine-generated order ID (string format)
            
        Returns:
            Tuple of (should_create_new, error_message, existing_order)
            - should_create_new: True if new order should be created
            - error_message: Error message key if order is invalid
            - existing_order: Order instance if exists and valid, None otherwise
        """
        logger.info(f"[check_order_existence] Checking order existence. order_id={order_id}")
        
        try:
            order = Order.objects.get(id=order_id)
            logger.info(
                f"[check_order_existence] Order found. "
                f"order_id={order_id}, status={order.status}, "
                f"expires_at={order.expires_at}"
            )
            
            # Check if order has expired
            if order.is_expired():
                logger.warning(
                    f"[check_order_existence] Order has expired. "
                    f"order_id={order_id}, expires_at={order.expires_at}, "
                    f"current_time={timezone.now()}"
                )
                return False, ERROR_MESSAGES['order_expired'], None
            
            # Check if order is in 'created' status
            if order.status == 'created':
                logger.info(
                    f"[check_order_existence] Valid existing order found. "
                    f"order_id={order_id}, will not create new order"
                )
                return False, None, order
            
            # Order exists but in different status
            logger.info(
                f"[check_order_existence] Order exists with status '{order.status}'. "
                f"order_id={order_id}, will create new order"
            )
            return True, None, None
            
        except Order.DoesNotExist:
            logger.info(
                f"[check_order_existence] Order not found. "
                f"order_id={order_id}, will create new order"
            )
            return True, None, None
    
    @staticmethod
    def check_device_online_status(device_uuid: str) -> Tuple[bool, Optional[str]]:
        """
        Checks if device is online by querying Tmetr heartbeat API.
        
        Args:
            device_uuid: UUID of the device to check
            
        Returns:
            Tuple of (is_online, error_message)
            - is_online: True if device is online, False otherwise
            - error_message: Error message key if device is offline or check fails
        """
        logger.info(
            f"[check_device_online_status] Checking device online status. "
            f"device_uuid={device_uuid}"
        )
        
        try:
            # Initialize Tmetr service
            tmetr_service = TmetrService()
            
            # Get device heartbeat
            logger.info(
                f"[check_device_online_status] Calling Tmetr heartbeat API. "
                f"device_uuid={device_uuid}"
            )
            heartbeat_response = tmetr_service.get_device_heartbeat(device_uuid)
            
            # Check if response contains heartbeat data
            if not heartbeat_response.get('content') or len(heartbeat_response['content']) == 0:
                logger.warning(
                    f"[check_device_online_status] No heartbeat data found for device. "
                    f"device_uuid={device_uuid}"
                )
                return False, ERROR_MESSAGES['device_offline']
            
            # Extract heartbeat timestamp
            heartbeat_data = heartbeat_response['content'][0]
            heartbeat_timestamp = heartbeat_data.get('heartbeatCreatedAt')
            
            if heartbeat_timestamp is None:
                logger.warning(
                    f"[check_device_online_status] Heartbeat timestamp missing. "
                    f"device_uuid={device_uuid}"
                )
                return False, ERROR_MESSAGES['heartbeat_check_failed']
            
            # Convert Unix timestamp to datetime (timestamp is in seconds)
            heartbeat_datetime = datetime.fromtimestamp(heartbeat_timestamp, tz=timezone.get_current_timezone())
            current_time = timezone.now()
            
            # Calculate time difference
            time_difference = current_time - heartbeat_datetime
            threshold_minutes = getattr(settings, 'DEVICE_ONLINE_THRESHOLD_MINUTES', 5)
            threshold_timedelta = timedelta(minutes=threshold_minutes)
            
            logger.info(
                f"[check_device_online_status] Heartbeat comparison. "
                f"device_uuid={device_uuid}, "
                f"heartbeat_time={heartbeat_datetime.isoformat()}, "
                f"current_time={current_time.isoformat()}, "
                f"time_difference={time_difference.total_seconds()} seconds, "
                f"threshold={threshold_minutes} minutes"
            )
            
            # Check if device is online
            if time_difference > threshold_timedelta:
                logger.warning(
                    f"[check_device_online_status] Device is offline. "
                    f"device_uuid={device_uuid}, "
                    f"last_heartbeat={heartbeat_datetime.isoformat()}, "
                    f"threshold_exceeded_by={time_difference - threshold_timedelta}"
                )
                return False, ERROR_MESSAGES['device_offline']
            
            logger.info(
                f"[check_device_online_status] Device is online. "
                f"device_uuid={device_uuid}, "
                f"last_heartbeat={heartbeat_datetime.isoformat()}"
            )
            return True, None
            
        except Exception as e:
            logger.error(
                f"[check_device_online_status] Error checking device status. "
                f"device_uuid={device_uuid}, error={str(e)}",
                exc_info=True
            )
            return False, ERROR_MESSAGES['heartbeat_check_failed']
    
    @staticmethod
    def execute_validation_chain(
        request_params: dict,
        device_uuid: str,
        order_id: str
    ) -> Dict[str, Any]:
        """
        Executes complete validation chain with early termination.
        
        Validation sequence:
        1. Hash validation
        2. Order existence check
        3. Device online status check
        
        Args:
            request_params: All request parameters for hash validation
            device_uuid: UUID of the device
            order_id: Machine-generated order ID (string format)
            
        Returns:
            Dictionary with validation results:
            {
                'valid': bool,
                'error_message': str | None,
                'existing_order': Order | None,
                'should_create_new_order': bool
            }
        """
        logger.info(
            f"[execute_validation_chain] Starting validation chain. "
            f"device_uuid={device_uuid}, order_id={order_id}, "
            f"request_params={list(request_params.keys())}"
        )
        
        # Step 1: Hash validation
        hash_valid, hash_error = OrderValidationService.validate_request_hash(request_params)
        if not hash_valid:
            logger.warning(
                f"[execute_validation_chain] Validation chain terminated: hash validation failed. "
                f"order_id={order_id}"
            )
            return {
                'valid': False,
                'error_message': hash_error,
                'existing_order': None,
                'should_create_new_order': False
            }
        
        # Step 2: Order existence check
        should_create_new, order_error, existing_order = OrderValidationService.check_order_existence(order_id)
        if order_error:
            logger.warning(
                f"[execute_validation_chain] Validation chain terminated: order validation failed. "
                f"order_id={order_id}, error={order_error}"
            )
            return {
                'valid': False,
                'error_message': order_error,
                'existing_order': None,
                'should_create_new_order': False
            }
        
        # Step 3: Device online status check
        device_online, device_error = OrderValidationService.check_device_online_status(device_uuid)
        if not device_online:
            logger.warning(
                f"[execute_validation_chain] Validation chain terminated: device status check failed. "
                f"device_uuid={device_uuid}, error={device_error}"
            )
            return {
                'valid': False,
                'error_message': device_error,
                'existing_order': None,
                'should_create_new_order': False
            }
        
        # All validations passed
        logger.info(
            f"[execute_validation_chain] Validation chain completed successfully. "
            f"device_uuid={device_uuid}, order_id={order_id}, "
            f"should_create_new_order={should_create_new}"
        )
        
        return {
            'valid': True,
            'error_message': None,
            'existing_order': existing_order,
            'should_create_new_order': should_create_new
        }
