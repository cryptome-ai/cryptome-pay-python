# Cryptome Pay Python SDK

> Official Python SDK for Cryptome Pay - Multi-chain cryptocurrency payment gateway

[![PyPI version](https://badge.fury.io/py/cryptomepay.svg)](https://pypi.org/project/cryptomepay/)
[![Python](https://img.shields.io/pypi/pyversions/cryptomepay.svg)](https://pypi.org/project/cryptomepay/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Installation

```bash
pip install cryptomepay
```

For async support:

```bash
pip install cryptomepay[async]
```

## Quick Start

```python
from cryptomepay import Client

client = Client(
    api_key='sk_live_your_api_key',
    api_secret='your_api_secret'
)

# Create a payment
payment = client.create_payment(
    order_id='ORDER_001',
    amount=100.00,
    notify_url='https://your-site.com/webhook',
    chain_type='BSC'
)

print(f"Payment URL: {payment['data']['payment_url']}")
print(f"Amount: {payment['data']['actual_amount']} USDT")
```

## Features

- **Multi-chain support**: TRC20, BSC, Polygon, Ethereum, Arbitrum
- **Non-custodial**: Payments go directly to your wallet
- **Type hints**: Full type annotation support
- **Async support**: Optional async client for high-performance applications
- **Framework integrations**: Works with Flask, Django, FastAPI

## Usage

### Create Payment

```python
from cryptomepay import Client, ChainType

client = Client(
    api_key='sk_live_xxx',
    api_secret='your_secret'
)

payment = client.create_payment(
    order_id='ORDER_001',
    amount=100.00,
    notify_url='https://example.com/webhook',
    redirect_url='https://example.com/success',  # Optional
    chain_type=ChainType.BSC
)

if payment['status_code'] == 200:
    data = payment['data']
    print(f"Trade ID: {data['trade_id']}")
    print(f"Pay {data['actual_amount']} USDT to {data['token']}")
    print(f"Payment URL: {data['payment_url']}")
```

### Query Payment

```python
# By trade_id
result = client.query_payment_by_trade_id('CP202312271648380592')

# By order_id
result = client.query_payment_by_order_id('ORDER_001')

if result['status_code'] == 200:
    order = result['data']
    print(f"Status: {order['status']}")  # 1=Pending, 2=Paid, 3=Expired
```

### List Orders

```python
from cryptomepay import PaymentStatus

orders = client.list_orders(
    page=1,
    page_size=20,
    status=PaymentStatus.PAID,
    chain_type='BSC',
    start_date='2025-12-01',
    end_date='2025-12-31'
)

for order in orders['data']['list']:
    print(f"{order['order_id']}: {order['actual_amount']} USDT")
```

### Verify Webhook Signature

```python
from flask import Flask, request

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    payload = request.get_json()

    if not client.verify_webhook_signature(payload):
        return 'Invalid signature', 401

    # Process payment
    if payload['status'] == 2:  # Paid
        order_id = payload['order_id']
        tx_hash = payload['block_transaction_id']
        # Fulfill order...

    return 'ok'
```

> **Sandbox Testing:** Use the Merchant Dashboard's built-in Sandbox page to test payment flows without real blockchain transactions.

## Async Client

```python
import asyncio
from cryptomepay import AsyncClient

async def main():
    client = AsyncClient(
        api_key='sk_live_xxx',
        api_secret='your_secret'
    )

    # Create payment
    payment = await client.create_payment(
        order_id='ORDER_001',
        amount=100.00,
        notify_url='https://example.com/webhook'
    )

    print(payment)

    # Don't forget to close the session
    await client.close()

asyncio.run(main())
```

### Async Context Manager

```python
async with AsyncClient(api_key='xxx', api_secret='secret') as client:
    payment = await client.create_payment(
        order_id='ORDER_001',
        amount=100.00,
        notify_url='https://example.com/webhook'
    )
```

## Framework Integrations

### Flask

```python
from flask import Flask, request, jsonify
from cryptomepay import Client
import os

app = Flask(__name__)
client = Client(
    api_key=os.environ['CRYPTOMEPAY_API_KEY'],
    api_secret=os.environ['CRYPTOMEPAY_API_SECRET']
)

@app.route('/api/payments', methods=['POST'])
def create_payment():
    data = request.get_json()

    payment = client.create_payment(
        order_id=f"ORD_{data['order_id']}",
        amount=data['amount'],
        notify_url=f"{request.host_url}webhooks/cryptomepay"
    )

    return jsonify(payment)

@app.route('/webhooks/cryptomepay', methods=['POST'])
def webhook():
    payload = request.get_json()

    if not client.verify_webhook_signature(payload):
        return 'Invalid signature', 401

    # Process payment...
    return 'ok'
```

### Django

```python
# views.py
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from cryptomepay import Client

client = Client(
    api_key=settings.CRYPTOMEPAY_API_KEY,
    api_secret=settings.CRYPTOMEPAY_API_SECRET
)

@require_POST
def create_payment(request):
    import json
    data = json.loads(request.body)

    payment = client.create_payment(
        order_id=f"ORD_{data['order_id']}",
        amount=data['amount'],
        notify_url=request.build_absolute_uri('/webhooks/cryptomepay/')
    )

    return JsonResponse(payment)

@csrf_exempt
@require_POST
def webhook(request):
    import json
    payload = json.loads(request.body)

    if not client.verify_webhook_signature(payload):
        return HttpResponse('Invalid signature', status=401)

    # Process payment...
    return HttpResponse('ok')
```

### FastAPI

```python
from fastapi import FastAPI, HTTPException, Request
from cryptomepay import AsyncClient
import os

app = FastAPI()
client = AsyncClient(
    api_key=os.environ['CRYPTOMEPAY_API_KEY'],
    api_secret=os.environ['CRYPTOMEPAY_API_SECRET']
)

@app.post('/api/payments')
async def create_payment(order_id: str, amount: float):
    payment = await client.create_payment(
        order_id=order_id,
        amount=amount,
        notify_url='https://example.com/webhooks/cryptomepay'
    )
    return payment

@app.post('/webhooks/cryptomepay')
async def webhook(request: Request):
    payload = await request.json()

    if not client.verify_webhook_signature(payload):
        raise HTTPException(status_code=401, detail='Invalid signature')

    # Process payment...
    return {'status': 'ok'}
```

## Constants

```python
from cryptomepay import ChainType, PaymentStatus, ErrorCode

# Chain types
ChainType.TRC20      # TRON network
ChainType.BSC        # BNB Smart Chain
ChainType.POLYGON    # Polygon PoS
ChainType.ETH        # Ethereum Mainnet
ChainType.ARBITRUM   # Arbitrum One

# Payment status
PaymentStatus.PENDING  # 1
PaymentStatus.PAID     # 2
PaymentStatus.EXPIRED  # 3

# Error codes
ErrorCode.SUCCESS           # 200
ErrorCode.BAD_REQUEST       # 400
ErrorCode.UNAUTHORIZED      # 401
ErrorCode.NOT_FOUND         # 404
ErrorCode.RATE_LIMITED      # 429
ErrorCode.INTERNAL_ERROR    # 500
```

## Error Handling

```python
from cryptomepay import Client, CryptomePayError, APIError, NetworkError

client = Client(api_key='xxx', api_secret='secret')

try:
    payment = client.create_payment(
        order_id='ORDER_001',
        amount=100.00,
        notify_url='https://example.com/webhook'
    )
except NetworkError as e:
    print(f"Network error: {e}")
except APIError as e:
    print(f"API error: {e.message}")
    print(f"Status code: {e.status_code}")
    print(f"Request ID: {e.request_id}")
except CryptomePayError as e:
    print(f"Error: {e}")
```

## API Reference

### Client

| Method | Description |
|--------|-------------|
| `create_payment(order_id, amount, notify_url, ...)` | Create a new payment |
| `query_payment_by_trade_id(trade_id)` | Query payment by trade_id |
| `query_payment_by_order_id(order_id)` | Query payment by order_id |
| `list_orders(page, page_size, ...)` | List orders with filters |
| `verify_webhook_signature(payload)` | Verify webhook signature |

### AsyncClient

Same methods as `Client`, but all are coroutines (use `await`).

Additional methods:
- `close()` - Close the aiohttp session
- Supports async context manager (`async with`)

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

- Documentation: https://docs.cryptomepay.com
- Email: support@cryptomepay.com
- GitHub Issues: https://github.com/cryptome-ai/cryptome-pay-python/issues
