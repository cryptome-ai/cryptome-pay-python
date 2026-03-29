"""
Cryptome Pay Python SDK

Official Python SDK for Cryptome Pay - Non-custodial cryptocurrency payment gateway.

Example usage::

    from cryptomepay import Client

    client = Client(
        api_key='sk_live_xxx',
        api_secret='your_secret'
    )

    payment = client.create_payment(
        order_id='ORDER_001',
        amount=100.00,
        notify_url='https://example.com/webhook',
        chain_type='BSC'
    )

    print(payment['data']['payment_url'])
"""

from cryptomepay.client import Client
from cryptomepay.async_client import AsyncClient
from cryptomepay.exceptions import CryptomePayError, AuthenticationError, ValidationError
from cryptomepay.constants import (
    VERSION,
    PRODUCTION_URL,
    ChainType,
    PaymentStatus,
    ErrorCode,
)

__version__ = VERSION
__all__ = [
    'Client',
    'AsyncClient',
    'CryptomePayError',
    'AuthenticationError',
    'ValidationError',
    'VERSION',
    'PRODUCTION_URL',
    'ChainType',
    'PaymentStatus',
    'ErrorCode',
]
