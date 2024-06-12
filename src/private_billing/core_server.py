from typing import Dict
from .network import (
    PeerToPeerBillingBaseServer,
    NodeInfo,
    no_verification_required,
    replies,
)
from .server import TCPAddress
from .core import (
    Bill,
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
    HiddenBillMessage,
    ConnectMessage,
    DataMessage,
    GetBillMessage,
    HiddenDataMessage,
    BillingMessageType,
    BillingMessageType,
    SeedMessage,
    UserType,
)


class CoreServer(PeerToPeerBillingBaseServer):

    def __post_init__(self) -> None:
        super().__post_init__()

        # Init
        self.mg = SharedMaskGenerator(Int64ToFloatConvertor(6, 4))
        self.hc: HidingContext = None
        self.contexts: Dict[CycleID, CycleContext] = {}
        self.bills: Dict[CycleID, Bill] = {}

    @property
    def role(self) -> UserType:
        return UserType.CORE

    @property
    def handlers(self):
        return {
            **super().handlers,
            BillingMessageType.GET_BILL: self.handle_get_bill,
            BillingMessageType.SEED: self.handle_seed,
            BillingMessageType.DATA: self.handle_data,
            BillingMessageType.HIDDEN_BILL: self.handle_hidden_bill,
            BillingMessageType.CYCLE_CONTEXT: self.handle_cycle_context,
        }

    def start(self, edge: TCPAddress, interval=1000) -> None:
        # Send connect request to edge server
        connect_msg = ConnectMessage(
            self.address, self.pk, self.role, self.network_members, self.billing_state
        )
        self.send(connect_msg, edge)

        # Start server
        return super().start(interval)

    ### Connect Message

    @no_verification_required
    def handle_connect(self, msg: ConnectMessage, origin: NodeInfo) -> None:
        super().handle_connect(msg, origin)

        cycle_length = msg.billing_state.get("cycle_length")
        if cycle_length and not self.hc:
            self.hc = HidingContext(cycle_length, self.mg)

        # Send seed message to connecting peer
        self.try_send_seed(origin)

    ### Seed Exchange

    def handle_seed(self, msg: SeedMessage, origin: NodeInfo) -> None:
        # Store seed
        self.mg.consume_foreign_seed(msg.seed, origin.id)

        # Send seed back, if necessary
        self.try_send_seed(origin)

    def try_send_seed(self, member: NodeInfo) -> None:
        """Send seed to address, if this has not happened before."""
        if not member.role == UserType.CORE:
            return

        has_seed_for_peer = self.mg.has_owned_seed_for_peer(member.id)
        if not has_seed_for_peer:
            self.send_seed(member)

    def send_seed(self, member: NodeInfo) -> None:
        """Send seed to `member`."""
        seed = self.mg.get_seed_for_peer(member.id)
        seed_msg = SeedMessage(self.address, seed)
        self.send(seed_msg, member)

    ### Forward data

    @no_verification_required
    def handle_data(self, msg: DataMessage, origin: NodeInfo) -> None:
        """Handle incoming `data` objects."""
        edge_nodes = filter(
            lambda x: x.role == UserType.EDGE, self.network_members.values()
        )
        for node in edge_nodes:
            self.send_data(msg.data, node)

    def send_data(self, data: Data, target: NodeInfo) -> None:
        """Send `data` to `target`."""
        hidden_data = data.hide(self.hc)
        hidden_data.client = self.id
        msg = HiddenDataMessage(self.address, hidden_data)
        self.send(msg, target)

    ### Handle incoming bill

    def handle_hidden_bill(self, msg: HiddenBillMessage, origin: NodeInfo) -> None:
        """Handle incoming `HiddenBill` objects."""
        hidden_bill = msg.hidden_bill
        bill = hidden_bill.reveal(self.hc)
        self.bills[bill.cycle_id] = bill

    ### Handle incoming bill request

    @replies
    @no_verification_required
    def handle_get_bill(self, msg: GetBillMessage, origin: NodeInfo) -> None:
        bill = self.bills.get(msg.cycle_id, None)
        self.reply(BillMessage(bill), origin)

    ### Handle Cycle Context

    @no_verification_required
    def handle_cycle_context(self, msg: ContextMessage, origin: NodeInfo) -> None:
        # do not use this
        pass


def launch_core(server_address: TCPAddress, edge: TCPAddress) -> None:
    """
    Launch core server
    :param server_address: address to host this server
    :param edge: information on edge to connect to network
    """
    server = CoreServer(server_address)
    server.start(edge)
