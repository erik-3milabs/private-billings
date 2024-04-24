from dataclasses import dataclass
import pickle
from typing import Any, Callable, Dict

from private_billing.core import (
    CycleContext,
    Data,
    HidingContext,
    Int64ToFloatConvertor,
    SharedMaskGenerator,
)
from private_billing.core import Bill, ClientID, CycleID
from private_billing.messages import (
    BillMessage,
    DataMessage,
    HelloMessage,
    Message,
    MessageType,
    NewMemberMessage,
    SeedMessage,
    UserType,
    Target
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


class Client:

    def __init__(self, market_operator: Target) -> None:
        self.id = None
        self.communicator = Communicator(self._receive)
        self.mg = SharedMaskGenerator(Int64ToFloatConvertor())
        self.hc: HidingContext = None
        self.context: Dict[CycleID, CycleContext] = {}
        self.billing_server: Target = None
        self.bills: Dict[CycleID, Bill] = {}

        # Register with the market_operator
        hello_msg = HelloMessage(UserType.CLIENT)
        self.communicator.send(hello_msg, market_operator)

    def _init_hiding_context(self, cyc: CycleContext) -> None:
        self.hc = HidingContext(cyc, self.mg)

    def _receive(self, msg: Message, sender: Target) -> None:
        call_backs = {
            MessageType.BILL: self._receive_bill,
            "info": self._receive_context,
            MessageType.NEW_MEMBER: self._new_member,
            MessageType.SEED: self._receive_seed,
            MessageType.WELCOME: self._welcome,
        }
        try:
            call_back = call_backs.get(msg.type)
            call_back(msg, sender)
        except IndexError:
            print(f"Recieved message of unknown type `{msg.type}`.")

    def _welcome(self, msg: Message) -> None:
        content = msg.content
        self.id = content.get("id")
        self.billing_server = content.get("billing_server")

        # Exchange seeds with registered peers
        peers = content.get("peers")
        for peer in peers:
            self._include_peer(peer)

        # Set up hiding context with info
        cyc_bytes = msg.content.get("cycle_context")
        cyc = CycleContext.deserialize(cyc_bytes)
        self._init_hiding_context(cyc)

    def _new_member(self, msg: NewMemberMessage, sender: Target) -> None:
        match msg.member_type:
            case UserType.CLIENT:
                peer = msg.new_member
                self._send_seed(peer)
            case UserType.SERVER:
                self.billing_server = msg.new_member

    def _send_seed(self, peer) -> None:
        seed = self.mg.get_seed_for_peer(peer.id)
        msg = SeedMessage(seed)
        self.communicator.send(msg, peer)

    def _receive_seed(self, msg: SeedMessage, sender: Target):
        self.mg.consume_foreign_seed(msg.seed, sender.id)

    def _receive_bill(self, msg: BillMessage, sender: Target):
        hb = msg.bill
        bill = hb.reveal(self.hc)
        self.bills[bill.cycle_id] = bill

    def _include_peer(self, peer: Target) -> None:
        if self.mg.has_seed_for_peer(peer):
            return
        self._send_seed(peer)

    def _receive_context(self, msg: Message) -> None:
        content = msg.content
        try:
            context_bytes = content.get("context_bytes")
            context = CycleContext.deserialize(context_bytes)
            self.context[context.id] = context
        except KeyError:
            print("received malformed 'receive_context' message.")

    def send_data(self, data: Data) -> None:
        hidden_data = data.hide(self.hc)
        hd_bytes = hidden_data.serialize()
        msg = DataMessage(hd_bytes)
        self.communicator.send(msg, self.billing_server)
