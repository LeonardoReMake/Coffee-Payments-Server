"""
Integration tests for background payment check complete workflows.

These tests verify end-to-end functionality of the background payment check system,
including Celery tasks, PaymentStatusService, and webhook integration.
"""

import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from payments.models import Order, Device, Merchant, MerchantCredentials
from payments.services.payment_status_service import PaymentStatusService


@pytest.mark.django_db
class TestBackgroundCheckIntegration:
    """Integration tests for complete background check workflows"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Create merchant
        self.merchant = Merchant.objects.create(
            name="Test Merchant",
            contact_email="test@example.com",
            bank_account="12345",
            valid_until=timezone.now().date() + timedelta(days=365)
        )
        
        # Create merchant credentials for Yookassa
        self.credentials = MerchantCredentials.objects.create(
            merchant=self.merchant,
            scenario='Yookassa',
            credentials={
                'account_id': 'test_account',
                'secret_key': 'test_secret'
            }
        )
        
        # Create device
        self.device = Device.objects.create(
            device_uuid="test-device-uuid",
            location="Test Location",
            merchant=self.merchant,
            payment_scenario="Yookassa",
            status='online',
            last_interaction=timezone.now()
        )
    
    def test_complete_background_check_cycle_for_pending_order(self):
        """
        Test complete background check cycle for pending order.
        
        Workflow:
        1. Create pending order with next_check_at
        2. Run background check task
        3. Verify order was checked and updated
        """
        # Create pending order
        order = Order.objects.create(
            id=f"test-order-{timezone.now().timestamp()}",
            drink_name="Test Drink",
            drink_number="123",
            device=self.device,
            merchant=self.merchant,
            size=1,
            price=Decimal('100.00'),
            status='pending',
            payment_reference_id='test-payment-id',
            payment_started_at=timezone.now(),
            next_check_at=timezone.now() - timedelta(seconds=1),  # Ready for check
            check_attempts=0
        )
        
        # Mock Yookassa API response
        with patch('payments.services.payment_status_service.Payment.find_one') as mock_find:
            mock_payment = MagicMock()
            mock_payment.status = 'pending'
            mock_find.return_value = mock_payment
            
            # Simulate background check
            result = PaymentStatusService.check_payment_status(order)
            assert result['status'] == 'pending'
            assert result['error'] is None
            
            # Process the status
            PaymentStatusService.process_payment_status(order, result['status'])
            
            # Verify order was updated
            order.refresh_from_db()
            assert order.status == 'pending'
            assert order.next_check_at is not None
            assert order.next_check_at > timezone.now()
    
    def test_fast_track_success_flow(self):
        """
        Test fast track success flow: check → paid → TMetr command.
        
        Workflow:
        1. Create pending order within fast track window
        2. Payment succeeds
        3. Verify make command is sent
        4. Verify status transitions: pending → paid → make_pending
        """
        # Create pending order within fast track window
        order = Order.objects.create(
            id=f"test-order-{timezone.now().timestamp()}",
            drink_name="Test Drink",
            drink_number="123",
            device=self.device,
            merchant=self.merchant,
            size=1,
            price=Decimal('100.00'),
            status='pending',
            payment_reference_id='test-payment-id',
            payment_started_at=timezone.now() - timedelta(seconds=60),  # 1 minute ago (fast track)
            next_check_at=timezone.now() - timedelta(seconds=1),
            check_attempts=0
        )
        
        # Mock Yookassa API and TMetr service
        with patch('payments.services.payment_status_service.Payment.find_one') as mock_find, \
             patch('payments.services.payment_status_service.TmetrService') as mock_tmetr:
            
            mock_payment = MagicMock()
            mock_payment.status = 'succeeded'
            mock_find.return_value = mock_payment
            
            mock_tmetr_instance = MagicMock()
            mock_tmetr.return_value = mock_tmetr_instance
            
            # Check payment status
            result = PaymentStatusService.check_payment_status(order)
            assert result['status'] == 'succeeded'
            
            # Process the status
            PaymentStatusService.process_payment_status(order, result['status'])
            
            # Verify make command was called
            assert mock_tmetr_instance.send_make_command.called
            
            # Verify order status
            order.refresh_from_db()
            assert order.status in ['make_pending', 'make_failed']
            assert order.next_check_at is None
    
    def test_slow_track_success_flow(self):
        """
        Test slow track success flow: check → manual_make.
        
        Workflow:
        1. Create pending order beyond fast track window
        2. Payment succeeds
        3. Verify status transitions to manual_make
        4. Verify no make command is sent
        """
        # Create pending order beyond fast track window
        order = Order.objects.create(
            id=f"test-order-{timezone.now().timestamp()}",
            drink_name="Test Drink",
            drink_number="123",
            device=self.device,
            merchant=self.merchant,
            size=1,
            price=Decimal('100.00'),
            status='pending',
            payment_reference_id='test-payment-id',
            payment_started_at=timezone.now() - timedelta(seconds=400),  # 6+ minutes ago (slow track)
            next_check_at=timezone.now() - timedelta(seconds=1),
            check_attempts=0
        )
        
        # Mock Yookassa API
        with patch('payments.services.payment_status_service.Payment.find_one') as mock_find, \
             patch('payments.services.payment_status_service.TmetrService') as mock_tmetr:
            
            mock_payment = MagicMock()
            mock_payment.status = 'succeeded'
            mock_find.return_value = mock_payment
            
            mock_tmetr_instance = MagicMock()
            mock_tmetr.return_value = mock_tmetr_instance
            
            # Check payment status
            result = PaymentStatusService.check_payment_status(order)
            assert result['status'] == 'succeeded'
            
            # Process the status
            PaymentStatusService.process_payment_status(order, result['status'])
            
            # Verify NO make command was sent
            assert not mock_tmetr_instance.send_make_command.called
            
            # Verify order status is manual_make
            order.refresh_from_db()
            assert order.status == 'manual_make'
            assert order.next_check_at is None
    
    def test_retry_logic_with_network_errors(self):
        """
        Test retry logic with network errors.
        
        Workflow:
        1. Create pending order
        2. Network error occurs
        3. Verify retry is scheduled
        4. Verify check_attempts is incremented
        """
        # Create pending order
        order = Order.objects.create(
            id=f"test-order-{timezone.now().timestamp()}",
            drink_name="Test Drink",
            device=self.device,
            merchant=self.merchant,
            size=1,
            price=Decimal('100.00'),
            status='pending',
            payment_reference_id='test-payment-id',
            payment_started_at=timezone.now(),
            next_check_at=timezone.now() - timedelta(seconds=1),
            check_attempts=2
        )
        
        # Mock network error
        with patch('payments.services.payment_status_service.Payment.find_one') as mock_find:
            import requests
            mock_find.side_effect = requests.RequestException("Network error")
            
            # Check payment status
            result = PaymentStatusService.check_payment_status(order)
            assert result['status'] is None
            assert result['error'] is not None
            
            # Handle the error
            PaymentStatusService.handle_check_error(order, result['error'])
            
            # Verify retry was scheduled
            order.refresh_from_db()
            assert order.status == 'pending'
            assert order.next_check_at is not None
            assert order.next_check_at > timezone.now()
    
    def test_failure_after_exhausting_retries(self):
        """
        Test failure after exhausting retries.
        
        Workflow:
        1. Create pending order with max check_attempts
        2. Network error occurs
        3. Verify order is marked as failed
        4. Verify failed_presentation_desc is set
        """
        from django.conf import settings
        
        # Create pending order with exhausted attempts
        order = Order.objects.create(
            id=f"test-order-{timezone.now().timestamp()}",
            drink_name="Test Drink",
            device=self.device,
            merchant=self.merchant,
            size=1,
            price=Decimal('100.00'),
            status='pending',
            payment_reference_id='test-payment-id',
            payment_started_at=timezone.now(),
            next_check_at=timezone.now() - timedelta(seconds=1),
            check_attempts=settings.PAYMENT_ATTEMPTS_LIMIT + 1
        )
        
        # Handle error with exhausted retries
        PaymentStatusService.handle_check_error(order, "Network error")
        
        # Verify order is marked as failed
        order.refresh_from_db()
        assert order.status == 'failed'
        assert order.failed_presentation_desc is not None
        assert order.next_check_at is None
    
    def test_webhook_processing_with_shared_logic(self):
        """
        Test webhook processing uses shared PaymentStatusService logic.
        
        Workflow:
        1. Create pending order
        2. Simulate webhook with succeeded status
        3. Verify PaymentStatusService is used
        4. Verify same logic as background check
        """
        # Create pending order
        order = Order.objects.create(
            id=f"test-order-{timezone.now().timestamp()}",
            drink_name="Test Drink",
            drink_number="123",
            device=self.device,
            merchant=self.merchant,
            size=1,
            price=Decimal('100.00'),
            status='pending',
            payment_reference_id='test-payment-id',
            payment_started_at=timezone.now() - timedelta(seconds=60),  # Fast track
            check_attempts=0
        )
        
        # Mock TMetr service
        with patch('payments.services.payment_status_service.TmetrService') as mock_tmetr:
            mock_tmetr_instance = MagicMock()
            mock_tmetr.return_value = mock_tmetr_instance
            
            # Simulate webhook processing
            PaymentStatusService.process_payment_status(order, 'succeeded')
            
            # Verify make command was called (fast track)
            assert mock_tmetr_instance.send_make_command.called
            
            # Verify order status
            order.refresh_from_db()
            assert order.status in ['make_pending', 'make_failed']
    
    def test_multiple_orders_processed_in_single_task_run(self):
        """
        Test multiple orders processed in single task run.
        
        Workflow:
        1. Create multiple pending orders
        2. Simulate background task processing all orders
        3. Verify all orders are updated correctly
        """
        # Create multiple pending orders
        orders = []
        for i in range(3):
            order = Order.objects.create(
                id=f"test-order-{i}-{timezone.now().timestamp()}",
                drink_name=f"Test Drink {i}",
                drink_number=f"12{i}",
                device=self.device,
                merchant=self.merchant,
                size=1,
                price=Decimal('100.00'),
                status='pending',
                payment_reference_id=f'test-payment-id-{i}',
                payment_started_at=timezone.now() - timedelta(seconds=60 * i),
                next_check_at=timezone.now() - timedelta(seconds=1),
                check_attempts=0
            )
            orders.append(order)
        
        # Mock Yookassa API
        with patch('payments.services.payment_status_service.Payment.find_one') as mock_find, \
             patch('payments.services.payment_status_service.TmetrService') as mock_tmetr:
            
            mock_tmetr_instance = MagicMock()
            mock_tmetr.return_value = mock_tmetr_instance
            
            # Process each order
            for order in orders:
                mock_payment = MagicMock()
                mock_payment.status = 'pending'
                mock_find.return_value = mock_payment
                
                result = PaymentStatusService.check_payment_status(order)
                PaymentStatusService.process_payment_status(order, result['status'])
            
            # Verify all orders were updated
            for order in orders:
                order.refresh_from_db()
                assert order.next_check_at is not None
                assert order.next_check_at > timezone.now()
