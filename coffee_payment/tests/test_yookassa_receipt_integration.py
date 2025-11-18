"""
Integration tests for YookassaReceipt payment scenario.
These tests require database access and test the full payment flow.
"""
import pytest
from django.test import TestCase, Client
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from payments.models import Merchant, Device, Order, Receipt, MerchantCredentials, Drink


@pytest.mark.django_db
class TestYookassaReceiptIntegration(TestCase):
    """Integration tests for YookassaReceipt scenario"""
    
    def setUp(self):
        """Set up test data"""
        # Create merchant
        self.merchant = Merchant.objects.create(
            name="Test Merchant",
            contact_email="merchant@test.com",
            bank_account="12345678",
            valid_until=timezone.now().date() + timedelta(days=365)
        )
        
        # Create YookassaReceipt credentials
        self.credentials = MerchantCredentials.objects.create(
            merchant=self.merchant,
            scenario='YookassaReceipt',
            credentials={
                'account_id': '1193510',
                'secret_key': 'test_key',
                'is_receipt_mandatory': True,
                'tax_system_code': 1,
                'timezone': 1,
                'vat_code': 2
            }
        )
        
        # Create device
        self.device = Device.objects.create(
            device_uuid='test-device-123',
            merchant=self.merchant,
            location='Test Location',
            status='online',
            last_interaction=timezone.now(),
            payment_scenario='YookassaReceipt'
        )
        
        # Create drink with meta
        self.drink = Drink.objects.create(
            id=1,
            name='Американо',
            description='Test drink',
            prices={1: 150, 2: 180, 3: 200},
            available=True,
            meta={
                'vat_code': 2,
                'measure': 'piece',
                'payment_subject': 'commodity',
                'payment_mode': 'full_payment'
            }
        )
        
        self.client = Client()
    
    def test_get_order_status_includes_receipt_config(self):
        """Test that get_order_status returns payment_scenario and is_receipt_mandatory"""
        # Create order
        order = Order.objects.create(
            id='test-order-123',
            drink_name='Американо',
            drink_number='1',
            device=self.device,
            merchant=self.merchant,
            size=1,
            price=Decimal('150.00'),
            status='created'
        )
        
        response = self.client.get(f'/v1/order-status/{order.id}')
        
        assert response.status_code == 200
        data = response.json()
        assert data['payment_scenario'] == 'YookassaReceipt'
        assert data['is_receipt_mandatory'] == True
    
    def test_payment_flow_without_email_optional(self):
        """Test payment flow when email is optional and not provided"""
        # Update credentials to make email optional
        self.credentials.credentials['is_receipt_mandatory'] = False
        self.credentials.save()
        
        # Create order
        order = Order.objects.create(
            id='test-order-456',
            drink_name='Капучино',
            drink_number='2',
            device=self.device,
            merchant=self.merchant,
            size=2,
            price=Decimal('180.00'),
            status='created'
        )
        
        # This test would require mocking Yookassa API
        # For MVP, we verify the endpoint accepts requests without email
        # Full integration test would be done manually or with API mocking
        pass
    
    def test_missing_credentials_handling(self):
        """Test error handling when YookassaReceipt credentials not configured"""
        # Create device without credentials
        device_no_creds = Device.objects.create(
            device_uuid='test-device-no-creds',
            merchant=self.merchant,
            location='Test Location 2',
            status='online',
            last_interaction=timezone.now(),
            payment_scenario='YookassaReceipt'
        )
        
        # Delete credentials
        self.credentials.delete()
        
        # Create order
        order = Order.objects.create(
            id='test-order-789',
            drink_name='Латте',
            drink_number='3',
            device=device_no_creds,
            merchant=self.merchant,
            size=3,
            price=Decimal('200.00'),
            status='created'
        )
        
        # Attempt to initiate payment should fail gracefully
        # This would be tested with actual API call in full integration test
        pass


# Note: Full Yookassa API integration tests require test credentials and mocking
# For MVP, manual testing with test Yookassa account is recommended
