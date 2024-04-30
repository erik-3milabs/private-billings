from socketserver import TCPServer
from common import CLIENT_PORT, MC
from private_billing.peer import Peer, PeerDataStore

import logging
logger = logging.getLogger(__name__)
logging.basicConfig()
logger.setLevel(logging.DEBUG)

if __name__ == "__main__":
    PeerDataStore().market_config = MC
    # Register with the market operator
    Peer.register(MC)

    # Launch server
    with TCPServer(("localhost", CLIENT_PORT), Peer) as server:
        server.serve_forever()
