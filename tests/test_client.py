"""Tests for the synchronous client."""

import pytest
import responses

from cryptomepay import Client, PRODUCTION_URL, SANDBOX_URL, PaymentStatus


@pytest.fixture
def client():
    """Create a test client."""
    return Client(
        api_key='sk_test_key',
        api_secret='test_secret'
    )


class TestClient:
    """Tests for Client class."""

    def test_init(self, client):
        """Test client initialization."""
        assert client.api_key == 'sk_test_key'
        assert client.api_secret == 'test_secret'
        assert client.base_url == PRODUCTION_URL

    def test_custom_base_url(self):
        """Test custom base URL."""
        client = Client(
            api_key='key',
            api_secret='secret',
            base_url='https://custom.example.com/api/v1/'
        )
        assert client.base_url == 'https://custom.example.com/api/v1'

    def test_use_sandbox(self, client):
        """Test switching to sandbox."""
        result = client.use_sandbox()
        assert client.base_url == SANDBOX_URL
        assert result is client  # Returns self for chaining

    def test_use_production(self, client):
        """Test switching to production."""
        client.use_sandbox()
        result = client.use_production()
        assert client.base_url == PRODUCTION_URL
        assert result is client


class TestSignature:
    """Tests for signature generation."""

    def test_generate_signature(self, client):
        """Test signature generation."""
        params = {
            'order_id': 'ORDER_001',
            'amount': '100.00',
            'notify_url': 'https://example.com/webhook',
        }

        signature1 = client._generate_signature(params)
        signature2 = client._generate_signature(params)

        assert len(signature1) == 32
        assert signature1 == signature2

    def test_signature_order_independent(self, client):
        """Test that parameter order doesn't matter."""
        params1 = {
            'order_id': 'ORDER_001',
            'amount': '100.00',
            'notify_url': 'https://example.com',
        }

        params2 = {
            'notify_url': 'https://example.com',
            'order_id': 'ORDER_001',
            'amount': '100.00',
        }

        assert client._generate_signature(params1) == client._generate_signature(params2)

    def test_signature_excludes_empty(self, client):
        """Test that empty values are excluded."""
        params1 = {
            'order_id': 'ORDER_001',
            'amount': '100.00',
        }

        params2 = {
            'order_id': 'ORDER_001',
            'amount': '100.00',
            'chain_type': '',
        }

        assert client._generate_signature(params1) == client._generate_signature(params2)


class TestWebhookVerification:
    """Tests for webhook signature verification."""

    def test_verify_valid_signature(self, client):
        """Test verification of valid signature."""
        params = {
            'trade_id': 'CP123',
            'order_id': 'ORDER_001',
            'amount': '100.00',
            'actual_amount': '15.6250',
            'token': '0xabc',
            'chain_type': 'BSC',
            'block_transaction_id': '0x123',
            'status': '2',
        }
        valid_signature = client._generate_signature(params)

        payload = {
            **params,
            'signature': valid_signature,
        }

        assert client.verify_webhook_signature(payload) is True

    def test_verify_invalid_signature(self, client):
        """Test rejection of invalid signature."""
        payload = {
            'trade_id': 'CP123',
            'order_id': 'ORDER_001',
            'amount': '100.00',
            'signature': 'invalid_signature_here',
        }

        assert client.verify_webhook_signature(payload) is False

    def test_verify_missing_signature(self, client):
        """Test rejection when signature is missing."""
        payload = {
            'trade_id': 'CP123',
            'order_id': 'ORDER_001',
        }

        assert client.verify_webhook_signature(payload) is False


class TestCreatePayment:
    """Tests for create_payment method."""

    @responses.activate
    def test_create_payment_success(self, client):
        """Test successful payment creation."""
        responses.add(
            responses.POST,
            f'{PRODUCTION_URL}/order/create-transaction',
            json={
                'status_code': 200,
                'message': 'success',
                'data': {
                    'trade_id': 'CP123456789',
                    'order_id': 'ORDER_001',
                    'amount': 100.00,
                    'actual_amount': 15.6250,
                    'token': '0xabc123',
                    'chain_type': 'BSC',
                    'payment_url': 'https://pay.example.com/CP123456789',
                },
                'request_id': 'req_123',
            },
            status=200,
        )

        result = client.create_payment(
            order_id='ORDER_001',
            amount=100.00,
            notify_url='https://example.com/webhook',
            chain_type='BSC',
        )

        assert result['status_code'] == 200
        assert result['data']['trade_id'] == 'CP123456789'
        assert result['data']['actual_amount'] == 15.6250

    @responses.activate
    def test_create_payment_with_redirect(self, client):
        """Test payment creation with redirect URL."""
        responses.add(
            responses.POST,
            f'{PRODUCTION_URL}/order/create-transaction',
            json={'status_code': 200, 'message': 'success', 'data': {}},
            status=200,
        )

        result = client.create_payment(
            order_id='ORDER_001',
            amount=100.00,
            notify_url='https://example.com/webhook',
            redirect_url='https://example.com/success',
        )

        assert result['status_code'] == 200


class TestQueryPayment:
    """Tests for query_payment methods."""

    @responses.activate
    def test_query_by_trade_id(self, client):
        """Test querying by trade_id."""
        responses.add(
            responses.GET,
            f'{PRODUCTION_URL}/order/query',
            json={
                'status_code': 200,
                'message': 'success',
                'data': {
                    'trade_id': 'CP123',
                    'order_id': 'ORDER_001',
                    'status': PaymentStatus.PAID,
                    'block_transaction_id': '0xdef456',
                },
            },
            status=200,
        )

        result = client.query_payment_by_trade_id('CP123')

        assert result['status_code'] == 200
        assert result['data']['status'] == PaymentStatus.PAID

    @responses.activate
    def test_query_by_order_id(self, client):
        """Test querying by order_id."""
        responses.add(
            responses.GET,
            f'{PRODUCTION_URL}/order/query',
            json={'status_code': 200, 'data': {'order_id': 'ORDER_001'}},
            status=200,
        )

        result = client.query_payment_by_order_id('ORDER_001')

        assert result['status_code'] == 200


class TestListOrders:
    """Tests for list_orders method."""

    @responses.activate
    def test_list_orders(self, client):
        """Test listing orders."""
        responses.add(
            responses.GET,
            f'{PRODUCTION_URL}/merchant/orders',
            json={
                'status_code': 200,
                'data': {
                    'list': [
                        {'trade_id': 'CP1', 'order_id': 'O1', 'status': 2},
                        {'trade_id': 'CP2', 'order_id': 'O2', 'status': 1},
                    ],
                    'total': 100,
                    'page': 1,
                    'page_size': 20,
                },
            },
            status=200,
        )

        result = client.list_orders(page=1, page_size=20)

        assert result['status_code'] == 200
        assert len(result['data']['list']) == 2
        assert result['data']['total'] == 100

    @responses.activate
    def test_list_orders_with_filters(self, client):
        """Test listing orders with filters."""
        responses.add(
            responses.GET,
            f'{PRODUCTION_URL}/merchant/orders',
            json={'status_code': 200, 'data': {'list': [], 'total': 0}},
            status=200,
        )

        result = client.list_orders(
            status=PaymentStatus.PAID,
            chain_type='BSC',
            start_date='2025-12-01',
            end_date='2025-12-31',
        )

        assert result['status_code'] == 200


class TestConstants:
    """Tests for constants."""

    def test_payment_status(self):
        """Test payment status values."""
        assert PaymentStatus.PENDING == 1
        assert PaymentStatus.PAID == 2
        assert PaymentStatus.EXPIRED == 3
