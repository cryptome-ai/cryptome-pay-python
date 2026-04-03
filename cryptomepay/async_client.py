"""Asynchronous client for Cryptome Pay API."""

import hashlib
import hmac
from typing import Any, Dict, Optional
from urllib.parse import urlencode

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

from cryptomepay.constants import VERSION, PRODUCTION_URL
from cryptomepay.exceptions import CryptomePayError


class AsyncClient:
    """
    Async Cryptome Pay API Client.

    Requires aiohttp: pip install cryptomepay[async]

    Example::

        import asyncio
        from cryptomepay import AsyncClient

        async def main():
            client = AsyncClient(
                api_key='sk_live_xxx',
                api_secret='your_secret'
            )

            payment = await client.create_payment(
                order_id='ORDER_001',
                amount=100.00,
                notify_url='https://example.com/webhook'
            )

        asyncio.run(main())
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = PRODUCTION_URL,
        timeout: int = 30
    ):
        """
        Initialize the async client.

        Args:
            api_key: Your API key
            api_secret: Your API secret
            base_url: API base URL (default: production)
            timeout: Request timeout in seconds (default: 30)
        """
        if not HAS_AIOHTTP:
            raise ImportError(
                "aiohttp is required for async support. "
                "Install with: pip install cryptomepay[async]"
            )

        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip('/')
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def headers(self) -> Dict[str, str]:
        """Get request headers."""
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': f'cryptomepay-python/{VERSION}',
        }

    async def __aenter__(self) -> 'AsyncClient':
        """Async context manager entry."""
        self._session = aiohttp.ClientSession(
            headers=self.headers,
            timeout=self.timeout
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._session:
            await self._session.close()
            self._session = None

    async def create_payment(
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

        return await self._request('POST', '/order/create-transaction', body)

    async def query_payment_by_trade_id(self, trade_id: str) -> Dict[str, Any]:
        """Query payment by trade_id."""
        return await self._request('GET', f'/order/query?trade_id={trade_id}')

    async def query_payment_by_order_id(self, order_id: str) -> Dict[str, Any]:
        """Query payment by order_id."""
        return await self._request('GET', f'/order/query?order_id={order_id}')

    async def list_orders(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[int] = None,
        chain_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """List orders with optional filters."""
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
        return await self._request('GET', f'/merchant/orders?{query}')

    async def get_merchant_info(self) -> Dict[str, Any]:
        """Get merchant profile."""
        return await self._request('GET', '/merchant/info')

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

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make async HTTP request."""
        url = f'{self.base_url}{endpoint}'

        # Create session if not using context manager
        session = self._session
        close_session = False

        if session is None:
            session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=self.timeout
            )
            close_session = True

        try:
            if method == 'GET':
                async with session.get(url) as response:
                    return await response.json()
            elif method == 'POST':
                async with session.post(url, json=data) as response:
                    return await response.json()
            elif method == 'PUT':
                async with session.put(url, json=data) as response:
                    return await response.json()
            else:
                raise ValueError(f'Unsupported method: {method}')

        except aiohttp.ClientError as e:
            raise CryptomePayError(f'Request failed: {e}')
        finally:
            if close_session:
                await session.close()
