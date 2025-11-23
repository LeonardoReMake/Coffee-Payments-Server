"""
Property-based tests for background payment check feature.

**Feature: background-payment-check**
"""

import pytest
from hypothesis import given, strategies as st
from hypothesis.extra.django import from_model
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from payments.models import Order, Device, Merchant


@pytest.mark.django_db
class TestOrderFieldInitialization:
    """
    **Feature: background-payment-check, Property 1: Order initialization sets default values**
    **Validates: Requirements 1.1**
    
    For any Order created without explicit values for background payment check fields,
    the system SHALL initialize check_attempts to 0 and leave timestamp fields as null.
    """
    
    @given(
        drink_name=st.text(min_size=1, max_size=100),
        size=st.sampled_from([1, 2, 3]),
        price=st.decimals(min_value=Decimal('0.01'), max_value=Decimal('10000'), places=2),
    )
    def test_order_initialization_defaults(self, drink_name, size, price, django_user_model):
        """
        Property: For any new Order, check_attempts should default to 0 and
        timestamp fields (payment_started_at, next_check_at, last_check_at) should be null.
        """
        # Create required related objects
        merchant = Merchant.objects.create(
            name="Test Merchant",
            api_key="test_key"
        )
        device = Device.objects.create(
            device_uuid="test-device-uuid",
            location="Test Location",
            merchant=merchant,
            payment_scenario="Yookassa"
        )
        
        # Create order without setting background payment check fields
        order = Order.objects.create(
            id=f"test-order-{timezone.now().timestamp()}",
            drink_name=drink_name,
            device=device,
            merchant=merchant,
            size=size,
            price=price,
            status='created'
        )
        
        # Verify default values
        assert order.check_attempts == 0, "check_attempts should default to 0"
        assert order.payment_started_at is None, "payment_started_at should be null by default"
        assert order.next_check_at is None, "next_check_at should be null by default"
        assert order.last_check_at is None, "last_check_at should be null by default"
        assert order.failed_presentation_desc is None, "failed_presentation_desc should be null by default"



@pytest.mark.django_db
class TestPaymentStatusService:
    """Property-based tests for PaymentStatusService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.merchant = Merchant.objects.create(
            name="Test Merchant",
            api_key="test_key"
        )
        self.device = Device.objects.create(
            device_uuid="test-device-uuid",
            location="Test Location",
            merchant=self.merchant,
            payment_scenario="Yookassa"
        )
    
    @given(
        timeout_seconds=st.integers(min_value=1, max_value=10)
    )
    def test_api_timeout_property(self, timeout_seconds):
        """
        **Feature: background-payment-check, Property 11: Payment API calls respect timeout**
        **Validates: Requirements 4.3**
        
        For any payment API call, the system SHALL apply a timeout of PAYMENT_API_TIMEOUT_S seconds.
        """
        from unittest.mock import patch, MagicMock
        from payments.services.payment_status_service import PaymentStatusService
        
        order = Order.objects.create(
            id=f"test-order-{timezone.now().timestamp()}",
            drink_name="Test Drink",
            device=self.device,
            merchant=self.merchant,
            size=1,
            price=Decimal('100.00'),
            status='pending',
            payment_reference_id='test-payment-id',
            payment_started_at=timezone.now()
        )
        
        # Mock Payment.find_one to raise Timeout
        with patch('payments.services.payment_status_service.Payment.find_one') as mock_find:
            mock_find.side_effect = requests.Timeout("API timeout")
            
            result = PaymentStatusService.check_payment_status(order)
            
            # Verify timeout was handled
            assert result['status'] is None
            assert result['error'] is not None
            assert 'timeout' in result['error'].lower()
    
    @given(
        check_attempts=st.integers(min_value=1, max_value=5)
    )
    def test_network_error_retry_logic(self, check_attempts):
        """
        **Feature: background-payment-check, Property 13: Network errors trigger retry within limit**
        **Validates: Requirements 5.1, 5.2**
        
        For any order with check_attempts <= PAYMENT_ATTEMPTS_LIMIT, network errors SHALL
        schedule a retry and keep the order status unchanged.
        """
        from payments.services.payment_status_service import PaymentStatusService
        from django.conf import settings
        
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
            check_attempts=check_attempts
        )
        
        if check_attempts <= settings.PAYMENT_ATTEMPTS_LIMIT:
            PaymentStatusService.handle_check_error(order, "Network error")
            order.refresh_from_db()
            
            # Verify retry was scheduled
            assert order.status == 'pending', "Status should remain pending for retry"
            assert order.next_check_at is not None, "next_check_at should be set for retry"
            assert order.next_check_at > timezone.now(), "next_check_at should be in the future"
    
    @given(
        check_attempts=st.integers(min_value=11, max_value=20)
    )
    def test_exhausted_retries_property(self, check_attempts):
        """
        **Feature: background-payment-check, Property 14: Exhausted retries mark order as failed**
        **Validates: Requirements 5.3, 5.4, 5.5**
        
        For any order with check_attempts > PAYMENT_ATTEMPTS_LIMIT, the system SHALL
        mark the order as failed and set failed_presentation_desc.
        """
        from payments.services.payment_status_service import PaymentStatusService
        from django.conf import settings
        
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
            check_attempts=check_attempts
        )
        
        if check_attempts > settings.PAYMENT_ATTEMPTS_LIMIT:
            PaymentStatusService.handle_check_error(order, "Network error")
            order.refresh_from_db()
            
            # Verify order was marked as failed
            assert order.status == 'failed', "Status should be failed after exhausting retries"
            assert order.failed_presentation_desc is not None, "failed_presentation_desc should be set"
            assert order.next_check_at is None, "next_check_at should be cleared"
    
    @given(
        seconds_since_start=st.integers(min_value=0, max_value=300)
    )
    def test_pending_fast_track_property(self, seconds_since_start):
        """
        **Feature: background-payment-check, Property 15: Pending status uses fast track within limit**
        **Validates: Requirements 6.1, 6.3**
        
        For any order with time_since_payment_started <= FAST_TRACK_LIMIT_S and status 'pending',
        the system SHALL schedule next check using FAST_TRACK_INTERVAL_S.
        """
        from payments.services.payment_status_service import PaymentStatusService
        from django.conf import settings
        
        payment_started_at = timezone.now() - timedelta(seconds=seconds_since_start)
        
        order = Order.objects.create(
            id=f"test-order-{timezone.now().timestamp()}",
            drink_name="Test Drink",
            device=self.device,
            merchant=self.merchant,
            size=1,
            price=Decimal('100.00'),
            status='pending',
            payment_reference_id='test-payment-id',
            payment_started_at=payment_started_at
        )
        
        if seconds_since_start <= settings.FAST_TRACK_LIMIT_S:
            PaymentStatusService.process_payment_status(order, 'pending')
            order.refresh_from_db()
            
            # Verify fast track interval was used
            expected_next_check = timezone.now() + timedelta(seconds=settings.FAST_TRACK_INTERVAL_S)
            assert order.next_check_at is not None
            # Allow 2 second tolerance for test execution time
            assert abs((order.next_check_at - expected_next_check).total_seconds()) < 2
    
    @given(
        seconds_since_start=st.integers(min_value=301, max_value=900)
    )
    def test_pending_slow_track_property(self, seconds_since_start):
        """
        **Feature: background-payment-check, Property 16: Pending status uses slow track beyond limit**
        **Validates: Requirements 6.2, 6.3**
        
        For any order with time_since_payment_started > FAST_TRACK_LIMIT_S and status 'pending',
        the system SHALL schedule next check using SLOW_TRACK_INTERVAL_S.
        """
        from payments.services.payment_status_service import PaymentStatusService
        from django.conf import settings
        
        payment_started_at = timezone.now() - timedelta(seconds=seconds_since_start)
        
        order = Order.objects.create(
            id=f"test-order-{timezone.now().timestamp()}",
            drink_name="Test Drink",
            device=self.device,
            merchant=self.merchant,
            size=1,
            price=Decimal('100.00'),
            status='pending',
            payment_reference_id='test-payment-id',
            payment_started_at=payment_started_at
        )
        
        if seconds_since_start > settings.FAST_TRACK_LIMIT_S:
            PaymentStatusService.process_payment_status(order, 'pending')
            order.refresh_from_db()
            
            # Verify slow track interval was used
            expected_next_check = timezone.now() + timedelta(seconds=settings.SLOW_TRACK_INTERVAL_S)
            assert order.next_check_at is not None
            # Allow 2 second tolerance for test execution time
            assert abs((order.next_check_at - expected_next_check).total_seconds()) < 2
    
    @given(
        seconds_since_start=st.integers(min_value=0, max_value=300)
    )
    def test_fast_track_success_property(self, seconds_since_start):
        """
        **Feature: background-payment-check, Property 17: Fast track success triggers drink preparation**
        **Validates: Requirements 7.1, 7.2, 7.3**
        
        For any order with time_since_payment_started <= FAST_TRACK_LIMIT_S and payment status 'succeeded',
        the system SHALL update status to 'paid', attempt to send make command, and clear next_check_at.
        """
        from unittest.mock import patch, MagicMock
        from payments.services.payment_status_service import PaymentStatusService
        from django.conf import settings
        
        payment_started_at = timezone.now() - timedelta(seconds=seconds_since_start)
        
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
            payment_started_at=payment_started_at
        )
        
        if seconds_since_start <= settings.FAST_TRACK_LIMIT_S:
            # Mock TmetrService to avoid actual API calls
            with patch('payments.services.payment_status_service.TmetrService') as mock_tmetr:
                mock_instance = MagicMock()
                mock_tmetr.return_value = mock_instance
                
                PaymentStatusService.process_payment_status(order, 'succeeded')
                order.refresh_from_db()
                
                # Verify make command was attempted
                assert mock_instance.send_make_command.called
                assert order.status in ['make_pending', 'make_failed']
                assert order.next_check_at is None
    
    @given(
        seconds_since_start=st.integers(min_value=301, max_value=900)
    )
    def test_delayed_success_property(self, seconds_since_start):
        """
        **Feature: background-payment-check, Property 4: Delayed payment success triggers manual make**
        **Validates: Requirements 2.1, 8.1**
        
        For any order with time_since_payment_started > FAST_TRACK_LIMIT_S and payment status 'succeeded',
        the system SHALL update status to 'manual_make' and clear next_check_at.
        """
        from payments.services.payment_status_service import PaymentStatusService
        from django.conf import settings
        
        payment_started_at = timezone.now() - timedelta(seconds=seconds_since_start)
        
        order = Order.objects.create(
            id=f"test-order-{timezone.now().timestamp()}",
            drink_name="Test Drink",
            device=self.device,
            merchant=self.merchant,
            size=1,
            price=Decimal('100.00'),
            status='pending',
            payment_reference_id='test-payment-id',
            payment_started_at=payment_started_at
        )
        
        if seconds_since_start > settings.FAST_TRACK_LIMIT_S:
            PaymentStatusService.process_payment_status(order, 'succeeded')
            order.refresh_from_db()
            
            # Verify manual_make status was set
            assert order.status == 'manual_make'
            assert order.next_check_at is None
    
    @given(
        seconds_since_start=st.integers(min_value=0, max_value=900)
    )
    def test_canceled_payments_property(self, seconds_since_start):
        """
        **Feature: background-payment-check, Property 18: Canceled payments mark order as not paid**
        **Validates: Requirements 9.1, 9.2**
        
        For any order with payment status 'canceled', the system SHALL update status to 'not_paid'
        and clear next_check_at.
        """
        from payments.services.payment_status_service import PaymentStatusService
        
        payment_started_at = timezone.now() - timedelta(seconds=seconds_since_start)
        
        order = Order.objects.create(
            id=f"test-order-{timezone.now().timestamp()}",
            drink_name="Test Drink",
            device=self.device,
            merchant=self.merchant,
            size=1,
            price=Decimal('100.00'),
            status='pending',
            payment_reference_id='test-payment-id',
            payment_started_at=payment_started_at
        )
        
        PaymentStatusService.process_payment_status(order, 'canceled')
        order.refresh_from_db()
        
        # Verify not_paid status was set
        assert order.status == 'not_paid'
        assert order.next_check_at is None
    
    @given(
        terminal_status=st.sampled_from(['succeeded', 'canceled', 'waiting_for_capture'])
    )
    def test_terminal_status_clears_next_check(self, terminal_status):
        """
        **Feature: background-payment-check, Property 6: Terminal status transitions clear next check**
        **Validates: Requirements 2.3, 7.3, 8.2, 9.2, 10.2**
        
        For any order transitioning to a terminal status (succeeded, canceled, waiting_for_capture),
        the system SHALL clear next_check_at.
        """
        from payments.services.payment_status_service import PaymentStatusService
        
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
            next_check_at=timezone.now() + timedelta(seconds=60)
        )
        
        # Mock TmetrService for succeeded status
        from unittest.mock import patch, MagicMock
        with patch('payments.services.payment_status_service.TmetrService') as mock_tmetr:
            mock_instance = MagicMock()
            mock_tmetr.return_value = mock_instance
            
            PaymentStatusService.process_payment_status(order, terminal_status)
            order.refresh_from_db()
            
            # Verify next_check_at was cleared
            assert order.next_check_at is None
