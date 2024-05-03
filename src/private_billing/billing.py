from .core import SharedBilling, ClientID, CycleID
from .peer import Target
from .messages import (
    DataMessage,
    HelloMessage,
    BillingMessageType,
    NewMemberMessage,
    UserType,
    WelcomeMessage,
)
from .server import (
    IP,
    MarketConfig,
    MessageHandler,
    MessageSender,
    Singleton,
)
from socketserver import TCPServer
import logging


class BillingServerDataStore(metaclass=Singleton):

    def __init__(self) -> None:
        self.shared_biller = SharedBilling()
        self.id: ClientID = None
        self.market_config: MarketConfig = None

    @property
    def market_operator(self):
        address = (self.market_config.market_host, self.market_config.market_port)
        return Target(None, address)


class BillingServer(MessageHandler):

    @property
    def data(self):
        return BillingServerDataStore()

    @property
    def handlers(self):
        return {
            BillingMessageType.WELCOME: self.handle_receive_welcome,
            BillingMessageType.NEW_MEMBER: self.handle_new_member,
            BillingMessageType.DATA: self.handle_receive_data,
        }

    @staticmethod
    def register(mc: MarketConfig) -> None:
        # Register with the market_operator
        market_operator = Target(None, (mc.market_host, mc.market_port))
        hello_msg = HelloMessage(UserType.SERVER)
        resp: WelcomeMessage = MessageSender.send(hello_msg, market_operator)

        ds = BillingServerDataStore()
        ds.id = resp.id

        # Include peers
        peer_ids = [p.id for p in resp.peers]
        for peer_id in peer_ids:
            ds.shared_biller.include_client(peer_id)

    def handle_receive_welcome(self, msg: WelcomeMessage, sender: Target) -> None:
        self.id = msg.id
        for peer in msg.peers:
            self.data.shared_biller.include_client(peer.id)

    def handle_new_member(self, msg: NewMemberMessage, sender: Target) -> None:
        if msg.member_type != UserType.CLIENT:
            return
        self.data.shared_biller.include_client(msg.new_member.id)

    def handle_receive_data(self, msg: DataMessage, sender: Target) -> None:
        # Register data
        self.data.shared_biller.record_data(msg.data, sender.id)

        # Attempt to start billing process
        self.attempt_billing(msg.data.cycle_id)

    def attempt_billing(self, cycle_id: CycleID) -> None:
        """Attempt to run the billing process for the given cycle"""
        if self.data.shared_biller.is_ready(cycle_id):
            self.data.shared_biller.compute_bills(cycle_id)


def launch_billing_server(
    market_config: MarketConfig, logging_level=logging.DEBUG, ip: IP = "localhost"
) -> None:
    # Specify logging setup
    logging.basicConfig()
    logger = logging.getLogger(__name__)
    logger.setLevel(logging_level)

    # Setup server
    BillingServerDataStore().market_config = market_config
    BillingServer.register(market_config)

    # Launch
    address = (ip, market_config.billing_port)
    logger.info(f"Going live on {address=}")
    with TCPServer(address, BillingServer) as server:
        server.serve_forever()
