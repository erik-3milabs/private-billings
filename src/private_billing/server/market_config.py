from dataclasses import dataclass
from .message_handler import IP


@dataclass
class MarketConfig:
    market_host: IP
    market_port: int
    billing_port: int
    peer_port: int
