from socketserver import TCPServer
from common import MARKET_HOST, MARKET_PORT, MC
from private_billing.market import MarketOperator, MarketOperatorDataStore

import logging
logger = logging.getLogger(__name__)
logging.basicConfig()
logger.setLevel(logging.DEBUG)


if __name__ == "__main__":
    ds = MarketOperatorDataStore()
    ds.market_config = MC
    ds.cycle_length = 1024    

    with TCPServer((MARKET_HOST, MARKET_PORT), MarketOperator) as server:
        server.serve_forever()
