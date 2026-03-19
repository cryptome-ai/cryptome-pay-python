"""Synchronous client for Cryptome Pay API."""

import hmac
import hashlib
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from cryptomepay.constants import VERSION, PRODUCTION_URL, SANDBOX_URL
from cryptomepay.exceptions import CryptomePayError


class Client:
    """
    Cryptome Pay API Client.

    Example::

        from cryptomepay import Client

        client = Client(
            api_key='sk_live_xxx',
            api_secret='your_secret'
        )

        payment = client.create_payment(
            order_id='ORDER_001',
            amount=100.00,
            notify_url='https://example.com/webhook'
        )
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = PRODUCTION_URL,
        timeout: int = 30
    ):
        """
        Initialize the client.

        Args:
            api_key: Your API key
            api_secret: Your API secret
            base_url: API base URL (default: production)
            timeout: Request timeout in seconds (default: 30)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': f'cryptomepay-python/{VERSION}',
        })

    def use_sandbox(self) -> 'Client':
        """Switch to sandbox environment."""
        self.base_url = SANDBOX_URL
        return self

    def use_production(self) -> 'Client':
        """Switch to production environment."""
        self.base_url = PRODUCTION_URL
        return self

    def create_payment(
        self,
        order_id: str,
        amount: float,
        notify_url: str,
        redirect_url: Optional[str] = None,
        chain_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new payment order.

        Args:
            order_id: Your unique order ID
            amount: Payment amount in CNY
            notify_url: Webhook callback URL
            redirect_url: Redirect URL after payment (optional)
            chain_type: Blockchain network (optional)

        Returns:
            API response dict
        """
        import time
        timestamp = str(int(time.time()))
        nonce = self._generate_nonce()

        params = {
            'api_key': self.api_key,
            'timestamp': timestamp,
            'nonce': nonce,
            'order_id': order_id,
            'amount': f'{amount:.2f}',
            'notify_url': notify_url,
        }

        if redirect_url:
            params['redirect_url'] = redirect_url
        if chain_type:
            params['chain_type'] = chain_type

        signature = self._generate_signature(params)

        body = {
            'api_key': self.api_key,
            'timestamp': timestamp,
            'nonce': nonce,
            'order_id': order_id,
            'amount': amount,
            'notify_url': notify_url,
            'signature': signature,
        }

        if redirect_url:
            body['redirect_url'] = redirect_url
        if chain_type:
            body['chain_type'] = chain_type

        return self._request('POST', '/order/create-transaction', body)

    def query_payment_by_trade_id(self, trade_id: str) -> Dict[str, Any]:
        """
        Query payment by trade_id.

        Args:
            trade_id: Cryptome Pay transaction ID

        Returns:
            API response dict
        """
        return self._request('GET', f'/merchant/order/query?trade_id={trade_id}')

    def query_payment_by_order_id(self, order_id: str) -> Dict[str, Any]:
        """
        Query payment by order_id.

        Args:
            order_id: Your order ID

        Returns:
            API response dict
        """
        return self._request('GET', f'/merchant/order/query?order_id={order_id}')

    def list_orders(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[int] = None,
        chain_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List orders with optional filters.

        Args:
            page: Page number (default: 1)
            page_size: Items per page (default: 20)
            status: Filter by status (1=pending, 2=paid, 3=expired)
            chain_type: Filter by chain
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            API response dict
        """
        params = {'page': page, 'page_size': page_size}

        if status:
            params['status'] = status
        if chain_type:
            params['chain_type'] = chain_type
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date

        query = urlencode(params)
        return self._request('GET', f'/merchant/orders?{query}')

    def get_merchant_info(self) -> Dict[str, Any]:
        """
        Get merchant profile.

        Returns:
            API response dict
        """
        return self._request('GET', '/merchant/info')

    def verify_webhook_signature(self, payload: Dict[str, Any]) -> bool:
        """
        Verify webhook payload signature (HMAC-SHA256).

        Args:
            payload: Webhook payload dict

        Returns:
            True if signature is valid
        """
        signature = payload.get('signature', '')
        if not signature:
            return False

        # Clone and filter params
        params = {}
        for k, v in payload.items():
            if k == 'signature':
                continue
            if v in ('', None):
                continue
            # Format amount fields correctly (handle both number and string types)
            if k == 'amount':
                try:
                    params[k] = f'{float(v):.2f}'
                except (ValueError, TypeError):
                    params[k] = str(v)
            elif k == 'actual_amount':
                try:
                    params[k] = f'{float(v):.4f}'
                except (ValueError, TypeError):
                    params[k] = str(v)
            else:
                params[k] = str(v)

        expected = self._calculate_signature(params)
        return hmac.compare_digest(expected.lower(), signature.lower())

    def _calculate_signature(self, params: Dict[str, str]) -> str:
        """Calculate HMAC-SHA256 signature."""
        # Filter and sort
        filtered = {
            k: v for k, v in params.items()
            if k != 'signature' and v not in ('', None)
        }
        sorted_params = sorted(filtered.items())

        # Build query string
        query_string = '&'.join(f'{k}={v}' for k, v in sorted_params)

        return hmac.new(
            self.api_secret.encode(),
            query_string.encode(),
            hashlib.sha256
        ).hexdigest()

    def _generate_signature(self, params: Dict[str, str]) -> str:
        """Generate HMAC-SHA256 signature."""
        # Filter and sort
        filtered = {
            k: v for k, v in params.items()
            if k != 'signature' and v not in ('', None)
        }
        sorted_params = sorted(filtered.items())

        # Build query string
        query_string = urlencode(sorted_params)

        # Generate HMAC-SHA256
        return hmac.new(
            self.api_secret.encode(),
            query_string.encode(),
            hashlib.sha256
        ).hexdigest()

    def _generate_nonce(self) -> str:
        """Generate a random nonce string."""
        import secrets
        return secrets.token_hex(16)

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request."""
        url = f'{self.base_url}{endpoint}'

        try:
            if method == 'GET':
                response = self.session.get(url, timeout=self.timeout)
            elif method == 'POST':
                response = self.session.post(url, json=data, timeout=self.timeout)
            elif method == 'PUT':
                response = self.session.put(url, json=data, timeout=self.timeout)
            else:
                raise ValueError(f'Unsupported method: {method}')

            return response.json()

        except requests.exceptions.Timeout:
            raise CryptomePayError('Request timeout')
        except requests.exceptions.RequestException as e:
            raise CryptomePayError(f'Request failed: {e}')
        except ValueError:
            raise CryptomePayError('Invalid JSON response')
