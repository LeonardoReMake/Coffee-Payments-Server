from yookassa import Configuration, Payment
# import var_dump as var_dump

Configuration.account_id = '1193510'
Configuration.secret_key = 'test_Ku1e9ZkX5OoTCm0k2m05Dg66XldJFHkER_9sw5LKE1E'

def create_payment(amount, description, return_url, drink_no, order_uuid, size):
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