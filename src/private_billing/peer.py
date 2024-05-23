import logging
from socketserver import TCPServer
from threading import Thread
from time import sleep
from typing import Any, Dict
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
    BillingMessageType,
    NewMemberMessage,
    SeedMessage,
    UserType,
    WelcomeMessage,
)
from .server import (
    ADDRESS,
    MessageHandler,
    MessageSender,
    Signature,
    Target,
    TransferablePublicKey,
    no_response,
)


class PeerDataStore:

    def __init__(self):
        self.id = None
        self.mg = SharedMaskGenerator(Int64ToFloatConvertor(6, 4))
        self.hc: HidingContext = None
        self.context: Dict[CycleID, CycleContext] = {}
        self.billing_server: Target = None
        self.server_public_key: TransferablePublicKey = None
        self.bills: Dict[CycleID, Bill] = {}
        self.market_address: ADDRESS = None

    @property
    def market_operator(self) -> Target:
        return Target(None, self.market_address)


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
        self.data.market_address = msg.market_address
        hello_msg = HelloMessage(UserType.CLIENT, self.contact_address)
        resp: WelcomeMessage = self.send(hello_msg, self.data.market_operator)

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
        self.data.server_public_key = msg.public_key

    def handle_receive_seed(self, msg: SeedMessage, sender: Target):
        """
        Handle receiving a seed from a peer.
        In this transaction, a different seed is immediately returned.

        This message is furthermore used to bootstrap peer-to-peer registration.
        """
        sender.id = msg.owner

        # Consume sent seed
        self.data.mg.consume_foreign_seed(msg.seed, sender.id)

        # Return seed
        seed = self.data.mg.get_seed_for_peer(sender.id)
        msg = SeedMessage(self.data.id, seed)
        self.reply(msg)

    @no_response
    def handle_receive_bill(self, msg: BillMessage, sender: Target):
        # Check signature
        verification_key = self.data.server_public_key
        is_valid = self.verify_signature(msg.bill, msg.signature, verification_key)

        # Discard invalid messages
        if not is_valid:
            return

        # Decrypt bill
        bill = msg.bill.reveal(self.data.hc)

        # Store result
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
        self.reply(BillMessage(bill, None))

    @no_response
    def handle_receive_data(self, msg: DataMessage, sender: Target) -> None:
        # encrypt and forward data to server
        self._send_data(msg.data)

    # Private functionality

    def _init_hiding_context(self, cycle_length: int) -> None:
        self.data.hc = HidingContext(cycle_length, self.data.mg)

    def register_with_peer(self, peer: Target) -> None:
        seed = self.data.mg.get_seed_for_peer(peer.id)
        msg = SeedMessage(self.data.id, seed)

        logging.debug(f"sending seed... {msg}")
        resp: SeedMessage = self.send(msg, peer)

        logging.debug(f"receiving seed... {resp}")
        self.data.mg.consume_foreign_seed(resp.seed, peer.id)

    def register_with_server(self, server: Target) -> None:
        self_ = Target(self.data.id, self.server.server_address)
        msg = NewMemberMessage(self_, UserType.CLIENT)
        import logging
        logging.debug(server)
        resp: NewMemberMessage = self.send(msg, server)
        self.data.server_public_key = resp.public_key

    def _send_data(self, data: Data) -> None:
        hidden_data = data.hide(self.data.hc)
        hidden_data.client = self.data.id
        msg = HiddenDataMessage(hidden_data)
        self.send(msg, self.data.billing_server)

    def verify_signature(
        self, obj: Any, signature: Signature, key: TransferablePublicKey
    ) -> bool:
        """
        Verify a signature is correct

        :param obj: object to check signature for
        :param signature: signature to check
        :param key: key to check signature against
        :return: whether signature is valid
        """
        try:
            key.verify_signature(obj, signature)
            return True
        except:
            return False


def launch_peer(
    server_address: ADDRESS,
    market_address: ADDRESS,
    logging_level=logging.DEBUG
) -> None:
    """
    Launch peer server

    :param logging_level: log level, defaults to logging.DEBUG
    :param server_address: address to host this server, defaults to ("localhost", 0)
    :param market_address: market operator address, defaults to ("localhost", 5555)
    """
    # Specify logging setup
    logging.basicConfig()
    logger = logging.getLogger(__name__)
    logger.setLevel(logging_level)

    # Launch server
    logger.info(f"Going live on {server_address=}")
    def serve():
        with TCPServer(server_address, Peer) as server:
            server.serve_forever()

    thread = Thread(target=serve)
    thread.start()
    
    # Allow server to boot up
    sleep(0.5)

    # Send boot message to server
    msg = BootMessage(market_address)
    target = Target(None, server_address)
    resp = MessageSender.send(msg, target)
    logger.debug(f"booted server: {resp}")
