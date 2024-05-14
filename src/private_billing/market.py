import logging
import socketserver
from typing import Dict, List, Tuple
import uuid

from private_billing.server.message_handler import ADDRESS
from .peer import Target
from .core import CycleContext, CycleID, ClientID
from .messages import (
    ContextMessage,
    HelloMessage,
    NewMemberMessage,
    UserType,
    WelcomeMessage,
    BillingMessageType,
)
from .server import (
    IP,
    MarketConfig,
    MessageHandler,
    Singleton,
)


class MarketOperatorDataStore(metaclass=Singleton):

    def __init__(self):
        self.cycle_length: int = -1
        self.cycle_contexts: Dict[CycleID, CycleContext] = {}
        self.participants: Dict[ADDRESS, Target] = {}
        self.billing_server: Target = None
        self.market_config: MarketConfig = None

    def get_peers(self, client: Target) -> List[Target]:
        """Get all peers for a given participant."""
        return [p for p in self.participants.values() if p.address != client.address]


class MarketOperator(MessageHandler):

    @property
    def data(self):
        return MarketOperatorDataStore()

    @property
    def handlers(self):
        return {
            BillingMessageType.HELLO: self.handle_hello,
            BillingMessageType.CYCLE_CONTEXT: self.handle_distribute_cycle_context,
        }

    def handle_hello(self, msg: HelloMessage, sender: Target) -> None:
        match msg.user_type:
            case UserType.CLIENT:
                self.register_new_client(msg.response_address)

            case UserType.SERVER:
                self.register_new_billing_server(msg.response_address)

    def register_new_client(self, response_address: ADDRESS) -> None:
        # Check if this client has not yet registered
        is_new = response_address not in self.data.participants
        if is_new:
            # New registration
            new_id = self._generate_new_uuid()
            client = Target(new_id, response_address)
            self.data.participants[client.address] = client
        else:
            # previously registered
            client = self.data.participants[response_address]

        # Return welcome message
        peers = self.data.get_peers(client)
        welcome_msg = WelcomeMessage(
            client.id, self.data.billing_server, peers, self.data.cycle_length
        )
        self.reply(welcome_msg)

    def register_new_billing_server(self, response_address: ADDRESS) -> None:
        known_server = self.data.billing_server
        is_new = not known_server or response_address != known_server.address
        if is_new:
            new_id = self._generate_new_uuid()
            server = Target(new_id, response_address)
            self.data.billing_server = server
        else:
            server = self.data.billing_server

        welcome_msg = WelcomeMessage(
            self.data.billing_server.id,
            self.data.billing_server,
            list(self.data.participants.values()),
            self.data.cycle_length,
        )
        self.reply(welcome_msg)

        if not is_new:
            return

        # Update participants of new server
        for peer in self.data.participants.values():
            # peer.address = peer.address[0], self.data.market_config.peer_port
            new_server_msg = NewMemberMessage(server, UserType.SERVER)
            self.send(new_server_msg, peer)

    def handle_distribute_cycle_context(self, msg: ContextMessage, sender: Target) -> None:
        """Forward cycle context to all participants and the billing server."""
        for peer in self.data.participants:
            self.send(msg, peer)
        self.send(msg, self.data.billing_server)

    def _generate_new_uuid(self) -> ClientID:
        return uuid.uuid4().int


if __name__ == "__main__":
    HOST, PORT = "localhost", 5555
    with socketserver.TCPServer((HOST, PORT), MarketOperator) as server:
        server.serve_forever()


def launch_market_operator(
    market_config: MarketConfig, logging_level=logging.DEBUG
) -> None:
    # Specify logging setup
    logging.basicConfig()
    logger = logging.getLogger(__name__)
    logger.setLevel(logging_level)

    # Setup server
    ds = MarketOperatorDataStore()
    ds.market_config = market_config
    ds.cycle_length = 1024

    # Launch
    address = (market_config.market_host, market_config.market_port)
    logger.info(f"Going live on {address=}")
    with socketserver.TCPServer(address, MarketOperator) as server:
        server.serve_forever()
