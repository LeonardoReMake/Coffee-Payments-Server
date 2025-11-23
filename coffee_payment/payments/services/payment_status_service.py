"""
Payment Status Service for background payment checking.

This service provides centralized logic for checking payment status from payment providers
and processing the results with time-based logic (fast/slow track).
"""

import logging
import requests
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from yookassa import Payment, Configuration
from payments.models import Order
from payments.services.tmetr_service import TmetrService

logger = logging.getLogger('payment_status_service')


class PaymentStatusService:
    """Service for checking and processing payment status"""
    
    @staticmethod
    def check_payment_status(order: Order) -> dict:
        """
        Check payment status for an order.
        
        Args:
            order: Order instance to check
            
        Returns:
            dict with keys:
                - 'status': Payment status from provider ('pending', 'succeeded', 'canceled', 'waiting_for_capture')
                - 'error': Error message if check failed (None if successful)
        """
        logger.info(f"Checking payment status for order {order.id}, payment_reference_id={order.payment_reference_id}, scenario={order.device.payment_scenario}")
        
        # Check if payment_reference_id exists
        if not order.payment_reference_id:
            error_msg = "Missing payment_reference_id"
            logger.error(f"Order {order.id}: {error_msg}")
            return {'status': None, 'error': error_msg}
        
        # Only check for Yookassa and YookassaReceipt scenarios
        if order.device.payment_scenario not in ['Yookassa', 'YookassaReceipt']:
            logger.info(f"Order {order.id}: Skipping payment check for scenario {order.device.payment_scenario}")
            return {'status': None, 'error': None}
        
        try:
            # Get merchant credentials
            merchant = order.merchant
            credentials = merchant.credentials.filter(scenario=order.device.payment_scenario).first()
            
            if not credentials:
                error_msg = f"No credentials found for scenario {order.device.payment_scenario}"
                logger.error(f"Order {order.id}: {error_msg}")
                return {'status': None, 'error': error_msg}
            
            # Configure Yookassa
            Configuration.account_id = credentials.credentials['account_id']
            Configuration.secret_key = credentials.credentials['secret_key']
            
            # Query Yookassa API with timeout
            logger.info(f"Order {order.id}: Querying Yookassa API for payment {order.payment_reference_id}")
            payment = Payment.find_one(order.payment_reference_id, timeout=settings.PAYMENT_API_TIMEOUT_S)
            
            payment_status = payment.status
            logger.info(f"Order {order.id}: Payment status from Yookassa: {payment_status}")
            
            return {'status': payment_status, 'error': None}
            
        except requests.Timeout as e:
            error_msg = f"Timeout querying payment provider: {str(e)}"
            logger.warning(f"Order {order.id}: {error_msg}")
            return {'status': None, 'error': error_msg}
            
        except requests.RequestException as e:
            error_msg = f"Network error querying payment provider: {str(e)}"
            logger.warning(f"Order {order.id}: {error_msg}")
            return {'status': None, 'error': error_msg}
            
        except Exception as e:
            error_msg = f"Unexpected error querying payment provider: {str(e)}"
            logger.error(f"Order {order.id}: {error_msg}")
            return {'status': None, 'error': error_msg}
    
    @staticmethod
    def process_payment_status(order: Order, payment_status: str) -> None:
        """
        Process payment status and update order accordingly.
        Applies time-based logic for fast/slow track.
        
        Args:
            order: Order instance to process
            payment_status: Status from payment provider
        """
        logger.info(f"Processing payment status for order {order.id}: status={payment_status}")
        
        now = timezone.now()
        time_since_payment_started = (now - order.payment_started_at).total_seconds() if order.payment_started_at else 0
        is_fast_track = time_since_payment_started <= settings.FAST_TRACK_LIMIT_S
        
        logger.info(f"Order {order.id}: time_since_payment_started={time_since_payment_started}s, is_fast_track={is_fast_track}")
        
        if payment_status == 'pending':
            # Keep status as pending, schedule next check
            if is_fast_track:
                order.next_check_at = now + timedelta(seconds=settings.FAST_TRACK_INTERVAL_S)
                logger.info(f"Order {order.id}: Pending (fast track), next check at {order.next_check_at}")
            else:
                order.next_check_at = now + timedelta(seconds=settings.SLOW_TRACK_INTERVAL_S)
                logger.info(f"Order {order.id}: Pending (slow track), next check at {order.next_check_at}")
            order.save()
            
        elif payment_status == 'succeeded':
            if is_fast_track:
                # Fast track: send drink preparation command
                logger.info(f"Order {order.id}: Payment succeeded (fast track), sending make command")
                order.status = 'paid'
                order.next_check_at = None
                order.save()
                
                # Send make command to TMetr API
                try:
                    tmetr_service = TmetrService()
                    tmetr_service.send_make_command(
                        device_id=order.device.device_uuid,
                        order_uuid=order.id,
                        drink_uuid=order.drink_number,
                        size=dict(Order._meta.get_field('size').choices)[order.size].lower(),
                        price=int(order.price)
                    )
                    order.status = 'make_pending'
                    order.save()
                    logger.info(f"Order {order.id}: Make command sent successfully, status updated to make_pending")
                except Exception as e:
                    logger.error(f"Order {order.id}: Failed to send make command: {str(e)}")
                    order.status = 'make_failed'
                    order.failed_presentation_desc = "Не удалось отправить команду на приготовление напитка"
                    order.save()
            else:
                # Slow track: mark as manual_make
                logger.info(f"Order {order.id}: Payment succeeded (slow track), marking as manual_make")
                order.status = 'manual_make'
                order.next_check_at = None
                order.save()
                
        elif payment_status == 'canceled':
            logger.info(f"Order {order.id}: Payment canceled, marking as not_paid")
            order.status = 'not_paid'
            order.next_check_at = None
            order.save()
            
        elif payment_status == 'waiting_for_capture':
            logger.info(f"Order {order.id}: Payment waiting_for_capture, marking as failed")
            order.status = 'failed'
            order.failed_presentation_desc = "Платеж требует ручного подтверждения"
            order.next_check_at = None
            order.save()
            
        else:
            logger.warning(f"Order {order.id}: Unknown payment status: {payment_status}")
    
    @staticmethod
    def handle_check_error(order: Order, error_message: str) -> None:
        """
        Handle payment check error with retry logic.
        
        Args:
            order: Order instance
            error_message: Error description
        """
        logger.info(f"Handling check error for order {order.id}: {error_message}, check_attempts={order.check_attempts}")
        
        now = timezone.now()
        
        if order.check_attempts <= settings.PAYMENT_ATTEMPTS_LIMIT:
            # Retry: keep status, schedule next check
            order.next_check_at = now + timedelta(seconds=settings.FAST_TRACK_INTERVAL_S)
            order.save()
            logger.info(f"Order {order.id}: Scheduling retry, next check at {order.next_check_at}")
        else:
            # Exhausted retries: mark as failed
            logger.error(f"Order {order.id}: Exhausted retry attempts, marking as failed")
            order.status = 'failed'
            order.failed_presentation_desc = "Не удалось проверить статус платежа. Пожалуйста, обратитесь в поддержку."
            order.next_check_at = None
            order.save()
