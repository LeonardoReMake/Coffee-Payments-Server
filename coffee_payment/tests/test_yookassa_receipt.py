"""
Unit tests for YookassaReceipt payment scenario.
"""
import pytest
from decimal import Decimal
from payments.services.yookassa_receipt_service import YookassaReceiptService


class TestBuildReceiptObject:
    """Tests for build_receipt_object method"""
    
    def test_build_receipt_with_drink_meta(self):
        """Test receipt uses values from drink_meta when available"""
        email = "test@example.com"
        drink_name = "Американо"
        amount = 150.0
        credentials = {
            'tax_system_code': 1,
            'timezone': 1,
            'vat_code': 1  # Should be overridden by drink_meta
        }
        drink_meta = {
            'vat_code': 2,
            'measure': 'piece',
            'payment_subject': 'commodity',
            'payment_mode': 'full_payment'
        }
        
        receipt = YookassaReceiptService.build_receipt_object(
            email, drink_name, amount, credentials, drink_meta
        )
        
        assert receipt['customer']['email'] == email
        assert receipt['items'][0]['description'] == drink_name
        assert receipt['items'][0]['vat_code'] == 2  # From drink_meta
        assert receipt['items'][0]['measure'] == 'piece'
        assert receipt['tax_system_code'] == 1
    
    def test_build_receipt_with_credential_fallback(self):
        """Test receipt uses credential values when drink_meta missing"""
        email = "test@example.com"
        drink_name = "Капучино"
        amount = 180.0
        credentials = {
            'tax_system_code': 1,
            'vat_code': 2,
            'measure': 'piece'
        }
        drink_meta = None
        
        receipt = YookassaReceiptService.build_receipt_object(
            email, drink_name, amount, credentials, drink_meta
        )
        
        assert receipt['items'][0]['vat_code'] == 2  # From credentials
        assert receipt['items'][0]['measure'] == 'piece'  # From credentials
    
    def test_build_receipt_excludes_missing_fields(self):
        """Test fields not in drink_meta or credentials are excluded"""
        email = "test@example.com"
        drink_name = "Латте"
        amount = 200.0
        credentials = {
            'tax_system_code': 1
        }
        drink_meta = {}
        
        receipt = YookassaReceiptService.build_receipt_object(
            email, drink_name, amount, credentials, drink_meta
        )
        
        # These fields should not be present
        assert 'vat_code' not in receipt['items'][0]
        assert 'measure' not in receipt['items'][0]
        assert 'payment_subject' not in receipt['items'][0]
        assert 'payment_mode' not in receipt['items'][0]
        
        # But required fields should be present
        assert receipt['customer']['email'] == email
        assert receipt['items'][0]['description'] == drink_name
        assert receipt['tax_system_code'] == 1


class TestEmailValidation:
    """Tests for email validation"""
    
    def test_valid_email_formats(self):
        """Test various valid email formats"""
        import re
        email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        
        valid_emails = [
            'test@example.com',
            'user.name@example.com',
            'user+tag@example.co.uk',
            'user123@test-domain.com'
        ]
        
        for email in valid_emails:
            assert re.match(email_pattern, email), f"{email} should be valid"
    
    def test_invalid_email_formats(self):
        """Test various invalid email formats"""
        import re
        email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        
        invalid_emails = [
            'invalid',
            '@example.com',
            'user@',
            'user @example.com',
            'user@example',
            ''
        ]
        
        for email in invalid_emails:
            assert not re.match(email_pattern, email), f"{email} should be invalid"


# Note: Integration tests and database-dependent tests should be in test_yookassa_receipt_integration.py
