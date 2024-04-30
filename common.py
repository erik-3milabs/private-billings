from private_billing.server.market_config import MarketConfig


MARKET_HOST, MARKET_PORT = "localhost", 5571
BILLING_PORT = 5551
CLIENT_PORT = 5543
MC = MarketConfig(MARKET_HOST, MARKET_PORT, BILLING_PORT, CLIENT_PORT)
