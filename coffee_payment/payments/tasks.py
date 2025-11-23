"""
Celery tasks for background payment checking.
"""

import logging
from celery import shared_task
from django.utils import timezone
from payments.models import Order
from payments.services.payment_status_service import PaymentStatusService

logger = logging.getLogger('check_pending_payments')


@shared_task
def check_pending_payments():
    """
    Background task to check payment status for pending orders.
    Runs periodically based on CELERY_BEAT_SCHEDULE configuration.
    """
    logger.info("Starting check_pending_payments task")
    
    now = timezone.now()
    
    # Query pending orders that need checking
    # Only process orders with status_check_type='polling'
    orders = Order.objects.filter(
        status='pending',
        status_check_type='polling',
        next_check_at__lte=now,
        next_check_at__isnull=False,
        expires_at__gt=now
    ).select_related('device', 'merchant').order_by('-payment_started_at')
    
    order_count = orders.count()
    logger.info(f"Found {order_count} pending orders to check (status_check_type='polling')")
    
    for order in orders:
        logger.info(f"Processing order {order.id}")
        
        # Update check tracking fields
        order.last_check_at = now
        order.check_attempts += 1
        order.save()
        
        # Check payment status
        result = PaymentStatusService.check_payment_status(order)
        
        if result['error']:
            # Handle error with retry logic
            PaymentStatusService.handle_check_error(order, result['error'])
        elif result['status']:
            # Process payment status
            PaymentStatusService.process_payment_status(order, result['status'])
        # If status is None and no error, it means we skipped the check (non-Yookassa scenario)
    
    logger.info(f"Completed check_pending_payments task, processed {order_count} orders")
    return order_count
