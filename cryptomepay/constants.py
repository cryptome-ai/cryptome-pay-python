"""Constants for Cryptome Pay SDK."""

from enum import Enum, IntEnum

# SDK Version
VERSION = "1.0.0"

# API URL
PRODUCTION_URL = "https://api.cryptomepay.com/api/v1"


class ChainType(str, Enum):
    """Supported blockchain networks."""
    TRC20 = "TRC20"
    BSC = "BSC"
    POLYGON = "POLYGON"
    ETH = "ETH"
    ARBITRUM = "ARBITRUM"


class PaymentStatus(IntEnum):
    """Payment status codes."""
    PENDING = 1
    PAID = 2
    EXPIRED = 3


class ErrorCode(IntEnum):
    """API error codes."""
    # Authentication errors
    INVALID_API_KEY = 1001
    SIGNATURE_VERIFY_FAILED = 1002
    API_KEY_EXPIRED = 1003
    IP_NOT_WHITELISTED = 1004
    MERCHANT_SUSPENDED = 1005

    # Order errors
    INVALID_ORDER_ID = 10001
    ORDER_EXISTS = 10002
    NO_AVAILABLE_WALLET = 10003
    INVALID_AMOUNT = 10004
    AMOUNT_CHANNEL_UNAVAILABLE = 10005
    EXCHANGE_RATE_ERROR = 10006
    ORDER_ALREADY_PAID = 10007
    ORDER_NOT_FOUND = 10008
    ORDER_EXPIRED = 10009

    # Chain errors
    INVALID_CHAIN_TYPE = 20001
    CHAIN_UNAVAILABLE = 20002
    CHAIN_MONITORING_DELAY = 20003

    # Rate limit errors
    RATE_LIMIT_EXCEEDED = 50001
    BURST_LIMIT_EXCEEDED = 50002
