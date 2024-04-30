from socketserver import TCPServer
from common import BILLING_PORT, MC
from private_billing.billing import BillingServer, BillingServerDataStore

import logging

logger = logging.getLogger(__name__)
logging.basicConfig()
logger.setLevel(logging.DEBUG)


if __name__ == "__main__":
    BillingServerDataStore().market_config = MC
    BillingServer.register(MC)

    with TCPServer(("localhost", BILLING_PORT), BillingServer) as server:
        server.serve_forever()
