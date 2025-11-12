from yookassa import Configuration, Payment
# import var_dump as var_dump

# Default credentials for backward compatibility
DEFAULT_ACCOUNT_ID = '1193510'
DEFAULT_SECRET_KEY = 'test_Ku1e9ZkX5OoTCm0k2m05Dg66XldJFHkER_9sw5LKE1E'

def create_payment(amount, description, return_url, drink_no, order_uuid, size, credentials=None):
    """
    Creates a Yookassa payment.
    
    Args:
        amount: Payment amount
        description: Payment description
        return_url: URL to redirect after payment
        drink_no: Drink number
        order_uuid: Order UUID
        size: Drink size
        credentials: Optional dict with 'account_id' and 'secret_key'. 
                    If not provided, uses default credentials for backward compatibility.
    
    Returns:
        Payment object from Yookassa API
    """
    # Use provided credentials or fall back to defaults
    if credentials:
        account_id = credentials['account_id']
        secret_key = credentials['secret_key']
    else:
        account_id = DEFAULT_ACCOUNT_ID
        secret_key = DEFAULT_SECRET_KEY
    
    # Configure Yookassa with the appropriate credentials
    Configuration.account_id = account_id
    Configuration.secret_key = secret_key
    
    payment = Payment.create(
        {
            "amount": {
                "value": f"{amount:.2f}",
                "currency": "RUB"
            },
            "capture": True,
            "confirmation": {
                "type": "redirect",
                "return_url": return_url
            },
            "description": description,
            "metadata": {
                "order_uuid": str(order_uuid),
                "drink_number": str(drink_no),
                "size": str(size)
            }
        }
    )
    
    return payment
    # payment_resonse = var_dump.var_dump(res)
    # return payment_resonse