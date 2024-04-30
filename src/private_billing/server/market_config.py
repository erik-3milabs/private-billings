from dataclasses import dataclass


@dataclass
class MarketConfig:
    market_host: str
    market_port: int
    billing_port: int
    peer_port: int
