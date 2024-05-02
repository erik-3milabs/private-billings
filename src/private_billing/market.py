import logging
import socketserver
from typing import Dict
import uuid
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
    MarketConfig,
    MessageHandler,
    MessageSender,
    Singleton,
)


class MarketOperatorDataStore(metaclass=Singleton):

    def __init__(self):
        self.cycle_length: int = -1
        self.cycle_contexts: Dict[CycleID, CycleContext] = {}
        self.participants: Dict[str, Target] = {}
        self.billing_server: Target = None
        self.market_config: MarketConfig = None

    def get_peers(self, client: Target) -> Dict[str, Target]:
        """Get all peers for a given participant."""
        return [p for p in self.participants.values() if p.ip != client.ip]


class MarketOperator(MessageHandler):

    @property
    def data(self):
        return MarketOperatorDataStore()

    @property
    def handlers(self):
        return {
            BillingMessageType.HELLO: self.handle_hello,
        }

    def handle_hello(self, msg: HelloMessage, sender: Target) -> None:
        match msg.user_type:
            case UserType.CLIENT:
                self.register_new_client(sender)

            case UserType.SERVER:
                self.register_new_billing_server(sender)

    def register_new_client(self, client: Target) -> None:
        # Check if this client has not yet registered
        is_new = client.ip not in self.data.participants
        if is_new:
            # New registration
            client.id = self._generate_new_uuid()
            self.data.participants[client.ip] = client
        else:
            # previously registered
            client = self.data.participants[client.ip]

        # Return welcome message
        peers = self.data.get_peers(client)
        welcome_msg = WelcomeMessage(
            client.id, self.data.billing_server, peers, self.data.cycle_length
        )
        self.reply(welcome_msg)

        if not is_new:
            return

        # Send subscribe message to other peers
        for peer in peers:
            new_subscriber_msg = NewMemberMessage(client, UserType.CLIENT)
            MessageSender.send(new_subscriber_msg, peer)

    def register_new_billing_server(self, server: Target) -> None:
        known_server = self.data.billing_server
        is_new = not known_server or server.ip != known_server.ip
        if is_new:
            server.id = self._generate_new_uuid()
            self.data.billing_server = server

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
            peer.address = peer.address[0], self.data.market_config.peer_port
            new_server_msg = NewMemberMessage(server, UserType.SERVER)
            MessageSender.send(new_server_msg, peer)

    def distribute_cycle_context(self, cyc: CycleContext) -> None:
        msg = ContextMessage(cyc)
        for peer in self.data.participants:
            MessageSender.send(msg, peer)
        MessageSender.send(self.data.billing_server, msg)

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
