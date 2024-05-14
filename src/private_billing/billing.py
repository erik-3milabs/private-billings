from threading import Thread
from typing import Dict

from private_billing.server.message_handler import MessageSender

from .core import SharedBilling, ClientID, CycleID
from .peer import Target
from .messages import (
    BillMessage,
    BootMessage,
    ContextMessage,
    HiddenDataMessage,
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
    no_response,
)
from socketserver import TCPServer
import logging


class BillingServerDataStore:

    def __init__(self) -> None:
        self.shared_biller = SharedBilling()
        self.id: ClientID = None
        self.market_config: MarketConfig = None
        self.participants: Dict[ClientID, Target] = {}

    @property
    def market_operator(self):
        address = (self.market_config.market_host, self.market_config.market_port)
        return Target(None, address)


class BillingServer(MessageHandler):

    @property
    def data(self):
        if not hasattr(self.server, "data"):
            self.server.data = BillingServerDataStore()
        return self.server.data

    @property
    def handlers(self):
        return {
            BillingMessageType.BOOT: self.handle_boot,
            BillingMessageType.CYCLE_CONTEXT: self.handle_receive_context,
            BillingMessageType.NEW_MEMBER: self.handle_new_member,
            BillingMessageType.HIDDEN_DATA: self.handle_receive_data,
        }

    def handle_boot(self, msg: BootMessage, sender: Target) -> None:
        """
        Perform boot sequence.
        This entails registering with the market operator.
        """

        # Register with the market_operator
        mc = msg.market_config
        market_operator = Target(None, (mc.market_host, mc.market_port))
        hello_msg = HelloMessage(UserType.SERVER, self.server.server_address)
        resp: WelcomeMessage = self.send(hello_msg, market_operator)

        # Store id
        self.data.id = resp.id

        # Register clients
        for peer in resp.peers:
            self.record_client(peer)
            self.register_with_client(peer)

        # Forward message to acknowledge boot success
        self.reply(resp)

    @no_response
    def handle_new_member(self, msg: NewMemberMessage, sender: Target) -> None:
        if msg.member_type != UserType.CLIENT:
            return
        self.record_client(msg.new_member)

    @no_response
    def handle_receive_context(self, msg: ContextMessage, sender: Target) -> None:
        self.data.shared_biller.record_contexts(msg.context)
        self.try_run_billing(msg.context.cycle_id)

    @no_response
    def handle_receive_data(self, msg: HiddenDataMessage, sender: Target) -> None:
        # Register data
        self.data.shared_biller.record_data(msg.data)

        # Attempt to start billing process
        self.try_run_billing(msg.data.cycle_id)

    def try_run_billing(self, cycle_id: CycleID) -> None:
        """Attempt to run the billing process for the given cycle"""
        if self.data.shared_biller.is_ready(cycle_id):
            self.run_billing(cycle_id)        

    def run_billing(self, cycle_id: CycleID) -> None:
        """Run the billing process for the given cycle"""
        bills = self.data.shared_biller.compute_bills(cycle_id)

        # Return bills to clients
        for id, client in self.data.participants.items():
            bill = bills[id]
            bill_msg = BillMessage(bill)
            self.send(bill_msg, client)

    def record_client(self, client: Target) -> None:
        # Record with self
        self.data.participants[client.id] = client

        # Record with the biller
        self.data.shared_biller.include_client(client.id)
        
    def register_with_client(self, client: Target) -> None:
        # Register with the peer
        self_ = Target(self.data.id, self.server.server_address)
        new_server = NewMemberMessage(self_, UserType.SERVER)
        self.send(new_server, client)

def launch_billing_server(
    market_config: MarketConfig, logging_level=logging.DEBUG, ip: IP = "localhost"
) -> None:
    # Specify logging setup
    logging.basicConfig()
    logger = logging.getLogger(__name__)
    logger.setLevel(logging_level)

    # Launch server
    address = (ip, market_config.billing_port)
    logger.info(f"Going live on {address=}")
    with TCPServer(address, BillingServer) as server:
        # Configure server
        bsds = BillingServerDataStore()
        bsds.market_config = market_config
        server.data = bsds
        
        # Start serving
        thread = Thread(target=server.serve_forever)
        thread.start()

        # Send boot message to server
        msg = BootMessage(market_config)
        target = Target(None, address)
        MessageSender.send(msg, target)
