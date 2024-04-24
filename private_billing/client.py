from dataclasses import dataclass
import pickle
from typing import Any, Callable, Dict

from private_billing import (
    CycleContext,
    Data,
    HidingContext,
    Int64ToFloatConvertor,
    SharedMaskGenerator,
)

MessageType = str


@dataclass
class Message:
    type: MessageType
    content: Dict


class Sender:
    pass


class Target:
    def __init__(self):
        pass

    def send(self, msg: Message) -> None:
        pass


class Communicator:

    def __init__(self, call_back: Callable[[Message, Sender], Any]):
        self.call_back = call_back

    def send(self, msg: Message, target: Target) -> None:
        msg_bytes = pickle.dumps(msg)
        target.send(target, msg_bytes)

    def receive(self, msg_bytes: bytes, sender: Sender) -> None:
        msg = pickle.loads(msg_bytes)
        self.call_back(msg, sender)


class Client:

    def __init__(self, market_operator: Target) -> None:
        self.id = None
        self.communicator = Communicator(self._receive)
        self.mg = SharedMaskGenerator(Int64ToFloatConvertor())
        self.hc: HidingContext = None
        self.context: Dict[int, CycleContext] = {}

        # Register with the market_operator
        hello_msg = Message("hello", {})
        self.communicator.send(hello_msg, market_operator)

    def _init_hiding_context(self, cyc: CycleContext) -> None:
        self.hc = HidingContext(cyc, self.mg)

    def _receive(self, msg: Message, sender: Sender) -> None:
        call_backs = {
            "bill": self._receive_bill,
            "info": self._receive_context,
            "new_subscriber": self._new_subscriber,
            "seed": self._receive_seed,
            "welcome": self._welcome,
        }
        call_back = call_backs.get(msg.type)
        call_back(msg, sender)

    def _welcome(self, msg: Message) -> None:
        content: Welcome = msg.content
        self.id = content.id
        self.billing_server = content.billing_server

        # Exchange seeds with registered peers
        peers = content.peers
        for peer in peers:
            self._include_peer(peer)

        # Set up hiding context with info
        cyc_bytes = msg.content.get("cycle_context")
        cyc = CycleContext.deserialize(cyc_bytes)
        self._init_hiding_context(cyc)

    def _new_subscriber(self, msg: Message) -> None:
        content = msg.content
        try:
            peer = content.get("new_subscriber")
            self._send_seed(peer)
        except KeyError:
            print("Received malformed 'new_subscribe' message.")

    def _send_seed(self, peer) -> None:
        seed = self.mg.get_seed_for_peer(peer.id)
        msg = Message("seed", {"seed": seed})
        self.communicator.send(msg, peer)

    def _receive_seed(self, msg: Message, sender: Sender):
        content = msg.content
        try:
            seed = content.get("seed")
            self.mg.consume_foreign_seed(seed, sender.id)
        except KeyError:
            print("Received malformed 'seed' message.")

    def _receive_bill(self, type, call_back: Callable):
        pass

    def _include_peer(self, peer: Peer) -> None:
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
        msg = Message("data", {"hidden_data_bytes": hd_bytes})
        self.communicator.send(msg, self.billing_server)
