import logging
import pickle
from socketserver import TCPServer
from threading import Thread
from typing import Any, Callable, Dict
from .core import (
    Bill,
    ClientID,
    CycleID,
    CycleContext,
    Data,
    HidingContext,
    Int64ToFloatConvertor,
    SharedMaskGenerator,
)
from .messages import (
    BillMessage,
    BootMessage,
    ContextMessage,
    DataMessage,
    GetBillMessage,
    GetContextMessage,
    HiddenDataMessage,
    HelloMessage,
    Message,
    BillingMessageType,
    NewMemberMessage,
    SeedMessage,
    UserType,
    WelcomeMessage,
)
from .server import (
    IP,
    MarketConfig,
    MessageHandler,
    MessageSender,
    Target,
    no_response,
)


class Communicator:

    def __init__(self, call_back: Callable[[Message, Target], Any]):
        self.call_back = call_back

    def send(self, msg: Message, target: Target) -> None:
        msg_bytes = pickle.dumps(msg)
        target.send(target, msg_bytes)

    def receive(self, msg_bytes: bytes, sender: Target) -> None:
        msg = pickle.loads(msg_bytes)
        self.call_back(msg, sender)


class PeerDataStore:

    def __init__(self):
        self.id = None
        self.mg = SharedMaskGenerator(Int64ToFloatConvertor(6, 4))
        self.hc: HidingContext = None
        self.context: Dict[CycleID, CycleContext] = {}
        self.peers: Dict[ClientID, Target] = {}
        self.billing_server: Target = None
        self.bills: Dict[CycleID, Bill] = {}
        self.market_config: MarketConfig = None

    @property
    def market_operator(self) -> Target:
        address = (self.market_config.market_host, self.market_config.market_port)
        return Target(None, address)


class Peer(MessageHandler):

    @property
    def data(self) -> PeerDataStore:
        if not hasattr(self.server, "data"):
            self.server.data = PeerDataStore()
        return self.server.data

    @property
    def handlers(self):
        return {
            BillingMessageType.BILL: self.handle_receive_bill,
            BillingMessageType.GET_BILL: self.handle_get_bill,
            BillingMessageType.BOOT: self.handle_boot,
            BillingMessageType.CYCLE_CONTEXT: self.handle_receive_context,
            BillingMessageType.GET_CYCLE_CONTEXT: self.handle_get_context,
            BillingMessageType.DATA: self.handle_receive_data,
            BillingMessageType.NEW_MEMBER: self.handle_new_member,
            BillingMessageType.SEED: self.handle_receive_seed,
        }

    # Handlers

    def handle_boot(self, msg: BootMessage, sender: Target) -> None:
        """
        Perform boot sequence.
        This entails registering with the market operator.
        """
        # Register with the market_operator
        mc = msg.market_config
        market_operator = Target(None, (mc.market_host, mc.market_port))
        hello_msg = HelloMessage(UserType.CLIENT, self.server.server_address)
        resp: WelcomeMessage = self.send(hello_msg, market_operator)

        # Store id
        self.data.id = resp.id
        self.data.billing_server = resp.billing_server

        # Set up hiding context with info
        self._init_hiding_context(resp.cycle_length)

        # Exchange seeds with registered peers
        for peer in resp.peers:
            self.register_with_peer(peer)

        # Register with billing server
        if self.data.billing_server:
            self.register_with_server(self.data.billing_server)

        # Forward message to acknowledge boot success
        self.reply(resp)

    @no_response
    def handle_new_member(self, msg: NewMemberMessage, sender: Target) -> None:
        assert msg.member_type == UserType.SERVER
        self.data.billing_server = msg.new_member

    def handle_receive_seed(self, msg: SeedMessage, sender: Target):
        """
        Handle receiving a seed from a peer.
        In this transaction, a different seed is immediately returned.

        This message is furthermore used to bootstrap peer-to-peer registration.
        """
        # Consume sent seed
        self.data.mg.consume_foreign_seed(msg.seed, sender.id)

        # Register peer
        self.data.peers[sender.id] = sender

        # Return seed
        seed = self.data.mg.get_seed_for_peer(sender.id)
        msg = SeedMessage(seed)
        self.reply(msg)

    @no_response
    def handle_receive_bill(self, msg: BillMessage, sender: Target):
        hb = msg.bill
        bill = hb.reveal(self.data.hc)
        self.data.bills[bill.cycle_id] = bill

    @no_response
    def handle_receive_context(self, msg: ContextMessage, sender: Target) -> None:
        context = msg.context
        self.data.context[context.cycle_id] = context

    def handle_get_context(self, msg: GetContextMessage, sender: Target) -> None:
        context = self.data.context.get(msg.cycle_id, None)
        self.reply(ContextMessage(context))

    def handle_get_bill(self, msg: GetBillMessage, sender: Target) -> None:
        bill = self.data.bills.get(msg.cycle_id, None)
        self.reply(BillMessage(bill))

    @no_response
    def handle_receive_data(self, msg: DataMessage, sender: Target) -> None:
        # encrypt and forward data to server
        self._send_data(msg.data)

    # Private functionality

    def _init_hiding_context(self, cycle_length: int) -> None:
        self.data.hc = HidingContext(cycle_length, self.data.mg)

    def register_with_peer(self, peer: Target) -> None:
        seed = self.data.mg.get_seed_for_peer(peer.id)
        msg = SeedMessage(seed)

        logging.debug(f"sending seed... {msg}")
        resp: SeedMessage = self.send(msg, peer)

        logging.debug(f"receiving seed... {resp}")
        self.data.mg.consume_foreign_seed(resp.seed, peer.id)

    def register_with_server(self, server: Target) -> None:
        self_ = Target(self.data.id, self.server.server_address)
        msg = NewMemberMessage(self_, UserType.CLIENT)
        self.send(msg, server)

    def _send_data(self, data: Data) -> None:
        hidden_data = data.hide(self.data.hc)
        hidden_data.client = self.data.id
        msg = HiddenDataMessage(hidden_data)
        self.send(msg, self.data.billing_server)


def launch_peer(
    market_config: MarketConfig, logging_level=logging.DEBUG, ip: IP = "localhost"
) -> None:
    # Specify logging setup
    logging.basicConfig()
    logger = logging.getLogger(__name__)
    logger.setLevel(logging_level)

    # Launch server
    address = (ip, market_config.peer_port)
    logger.info(f"Going live on {address=}")
    with TCPServer(address, Peer) as server:
        thread = Thread(target=server.serve_forever)
        thread.start()

        # Send boot message to server
        msg = BootMessage(market_config)
        target = Target(None, address)
        MessageSender.send(msg, target)
