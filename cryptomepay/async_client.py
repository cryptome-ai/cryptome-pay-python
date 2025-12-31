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

from cryptomepay.constants import VERSION, PRODUCTION_URL, SANDBOX_URL
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

    def use_sandbox(self) -> 'AsyncClient':
        """Switch to sandbox environment."""
        self.base_url = SANDBOX_URL
        return self

    def use_production(self) -> 'AsyncClient':
        """Switch to production environment."""
        self.base_url = PRODUCTION_URL
        return self

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
        params = {
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
        """Verify webhook payload signature."""
        signature = payload.get('signature', '')
        if not signature:
            return False

        params = {k: str(v) for k, v in payload.items() if k != 'signature'}
        expected = self._generate_signature(params)

        return hmac.compare_digest(expected, signature)

    def _generate_signature(self, params: Dict[str, str]) -> str:
        """Generate MD5 signature."""
        filtered = {
            k: v for k, v in params.items()
            if k != 'signature' and v not in ('', None)
        }
        sorted_params = sorted(filtered.items())
        query_string = urlencode(sorted_params)
        sign_string = query_string + self.api_secret
        return hashlib.md5(sign_string.encode()).hexdigest()

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
