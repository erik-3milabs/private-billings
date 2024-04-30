import logging
import pickle
from socketserver import TCPServer
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
    ContextMessage,
    DataMessage,
    HelloMessage,
    Message,
    BillingMessageType,
    NewMemberMessage,
    SeedMessage,
    UserType,
    WelcomeMessage,
)
from .server import (
    MarketConfig,
    MessageHandler,
    MessageSender,
    Target,
    Singleton,
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


class PeerDataStore(metaclass=Singleton):

    def __init__(self):
        self.id = None
        self.mg = SharedMaskGenerator(Int64ToFloatConvertor(6, 4))
        self.hc: HidingContext = None
        self.context: Dict[CycleID, CycleContext] = {}
        self.peers: Dict[ClientID, Target] = {}
        self.billing_server: Target = None
        self.bills: Dict[CycleID, Bill] = {}
        self.market_config: MarketConfig = None


class Peer(MessageHandler):

    @property
    def data(self):
        return PeerDataStore()

    @staticmethod
    def register(mc: MarketConfig) -> None:
        # Register with the market_operator
        mo = Target(None, (mc.market_host, mc.market_port))
        hello_msg = HelloMessage(UserType.CLIENT)
        resp: WelcomeMessage = MessageSender.send(hello_msg, mo)

        ds = PeerDataStore()
        ds.id = resp.id
        ds.billing_server = resp.billing_server

    @property
    def handlers(self):
        return {
            BillingMessageType.BILL: self.handle_receive_bill,
            BillingMessageType.CYCLE_CONTEXT: self.handle_receive_context,
            BillingMessageType.NEW_MEMBER: self.handle_new_member,
            BillingMessageType.SEED: self.handle_receive_seed,
            BillingMessageType.WELCOME: self.handle_welcome,
        }

    # Handlers

    def handle_welcome(self, msg: WelcomeMessage) -> None:
        # Set up hiding context with info
        self._init_hiding_context(msg.cycle_length)

        # Exchange seeds with registered peers
        for peer in msg.peers:
            self._include_peer(peer)

    def handle_new_member(self, msg: NewMemberMessage, sender: Target) -> None:
        match msg.member_type:
            case UserType.CLIENT:
                peer = msg.new_member
                self.data.peers[peer.id] = peer
            case UserType.SERVER:
                self.data.billing_server = msg.new_member

    def handle_receive_seed(self, msg: SeedMessage, sender: Target):
        self.data.mg.consume_foreign_seed(msg.seed, sender.id)

    def handle_receive_bill(self, msg: BillMessage, sender: Target):
        hb = msg.bill
        bill = hb.reveal(self.hc)
        self.data.bills[bill.cycle_id] = bill

    def handle_receive_context(self, msg: ContextMessage) -> None:
        context = msg.context
        self.data.context[context.cycle_id] = context

    # Private functionality

    def _init_hiding_context(self, cycle_length: int) -> None:
        self.hc = HidingContext(cycle_length, self.data.mg)

    def _send_seed(self, peer: Target) -> None:
        seed = self.data.mg.get_seed_for_peer(peer.id)
        msg = SeedMessage(seed)
        MessageSender.send(msg, peer)

    def _include_peer(self, peer: Target) -> None:
        if self.data.mg.has_seed_for_peer(peer):
            return
        self._send_seed(peer)

    def _send_data(self, data: Data) -> None:
        hidden_data = data.hide(self.hc)
        hd_bytes = hidden_data.serialize()
        msg = DataMessage(hd_bytes)
        MessageSender.send(msg, self.data.billing_server)


def launch_peer(
    market_config: MarketConfig, logging_level=logging.DEBUG, ip: str = "localhost"
) -> None:
    # Specify logging setup
    logging.basicConfig()
    logger = logging.getLogger(__name__)
    logger.setLevel(logging_level)

    # Register with the market operator
    PeerDataStore().market_config = market_config
    Peer.register(market_config)

    # Launch server
    with TCPServer((ip, market_config.peer_port), Peer) as server:
        server.serve_forever()
