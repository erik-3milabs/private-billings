from dataclasses import dataclass
from multiprocessing.pool import ThreadPool
from typing import Callable, Dict, Iterable, Tuple
import hashlib

from .messages import ConnectMessage, BillingMessageType, SignedMessage, UserType
from .server import (
    NotificationServer,
    Message,
    Signer,
    TransferablePublicKey,
    PickleEncoder,
    TCPAddress,
)


@dataclass
class NodeInfo:
    address: TCPAddress
    pk: TransferablePublicKey
    role: UserType

    @property
    def id(self) -> int:
        digest = hashlib.sha256(self.pk.public_key_bytes).digest()
        return int.from_bytes(digest, "little") % pow(2, 64)

    def __hash__(self) -> int:
        return hash((self.address, self.pk, self.role))


MessageHandler = Callable[[Message, NodeInfo], None]


def no_verification_required(func):
    """Decorator for handlers that require no signature verification."""
    func.require_verification = False
    return func


class NoValidSignatureException(Exception):
    pass


class PeerToPeerBillingBaseServer(NotificationServer):
    """
    Base server for the PeerToPeer Billing network
    Implements Network discovery layer
    """

    def __init__(self, address=TCPAddress("localhost", 5555)) -> None:
        super().__init__(PickleEncoder)
        self.address = address

        # Initialize Signer
        self.signer = Signer()
        self._node_info = NodeInfo(self.address, self.pk, self.role)

        # Add self to network
        self.network_members = {self.address: self._node_info}
        self.billing_state = {}

        # Setup threadpool to handle incoming requests
        self.tp = ThreadPool(processes=1)

    @property
    def id(self) -> int:
        """ID of this server."""
        return self._node_info.id

    @property
    def role(self) -> UserType:
        """Network role of this server."""
        raise NotImplementedError()

    @property
    def pk(self) -> TransferablePublicKey:
        """Public key of this server"""
        return self.signer.get_transferable_public_key()

    @property
    def handlers(self) -> Dict[BillingMessageType, MessageHandler]:
        """Message type to handler function map."""
        return {
            BillingMessageType.CONNECT: self.handle_connect,
        }

    @property
    def network_peers(self) -> Iterable[NodeInfo]:
        """All other nodes in the network."""
        return set(self.network_members.values()).difference({self._node_info})

    @property
    def network_edges(self) -> Iterable[NodeInfo]:
        """All edge nodes in the network."""
        return filter(lambda x: x.role == UserType.EDGE, self.network_members.values())

    @property
    def network_cores(self) -> Iterable[NodeInfo]:
        """All core nodes in the network."""
        return filter(lambda x: x.role == UserType.CORE, self.network_members.values())

    def start(self, interval: int = 1000) -> None:
        super().start(self.address.port, interval)

    def send(
        self, msg: Message, target: TCPAddress | NodeInfo, sign: bool = True
    ) -> None:
        """
        Send `msg` to `target`.

        :param msg: message to send
        :param target: target to send message to
        :param sign: whether to sign message before sending, defaults to True
        """
        if isinstance(target, NodeInfo):
            target = target.address
        if sign:
            msg = self.sign_msg(msg)
        super().send(msg, target)

    def sign_msg(self, msg: Message) -> SignedMessage:
        """Sign message before sending."""
        msg = self.encoder.encode(msg)
        sig = self.signer.sign(msg)
        return SignedMessage(msg, sig)

    def broadcast(self, msg: Message, targets: set[NodeInfo]) -> None:
        targets = map(lambda x: x.address, targets)
        return super().broadcast(msg, targets)

    def _handle(self, msg: Message) -> None:
        """Handle an incoming message"""
        # Handle signature
        msg, has_valid_signature = self.verify_signature(msg)

        msg_type = BillingMessageType(msg.type.value)
        handler = self.handlers.get(msg_type, self._fallback_handler)

        # Validity check
        requires_validation = getattr(handler, "require_verification", True)
        if requires_validation and not has_valid_signature:
            raise NoValidSignatureException()

        origin = self.get_node_info(msg.reply_address)
        self._execute(handler, msg, origin)

    def _execute(self, handler: Callable, *args) -> None:
        """Execute message handler."""
        self.tp.apply_async(handler, args=args)

    def _fallback_handler(self, msg: Message, origin: NodeInfo) -> None:
        print(
            f"ERROR: received message of {msg.type=} from {origin=}, which I cannot handle."
        )

    @no_verification_required
    def handle_connect(self, msg: ConnectMessage, origin: NodeInfo) -> None:
        """Handle connect request."""
        origin.pk = msg.pk
        origin.role = msg.role

        # Check network state difference
        other_network_state = msg.network_state
        other_address_set = set(other_network_state.keys())
        known_address_set = set(self.network_members.keys())

        # Register unknown addresses
        unknown_addresses = other_address_set.difference(known_address_set)
        for unknown_address in unknown_addresses:
            # Locally register to unknown network member
            new_node = other_network_state[unknown_address]
            self.register_node(new_node)

            # Connect with unknown peer
            unknown_member = self.get_node_info(unknown_address)
            self.send_connect(unknown_member)

    def register_node(self, node: NodeInfo) -> None:
        """Locally register `node`."""
        self.network_members[node.address] = node

    def send_connect(self, target: NodeInfo) -> None:
        """Send ConnectMessage to `target`"""
        msg = ConnectMessage(
            self.address, self.pk, self.role, self.network_members, self.billing_state
        )
        self.send(msg, target.address)

    def verify_signature(self, msg: Message) -> Tuple[Message, bool]:
        """Verify validity of a signed message."""
        if not isinstance(msg, SignedMessage):
            return msg, False

        # Extract message origin
        decoded_msg: Message = self.encoder.decode(msg.message)
        origin = self.get_node_info(decoded_msg.reply_address)

        # Verify signature
        has_valid_signature = origin.pk and origin.pk.verify_signature(
            msg.message, msg.signature
        )
        return (decoded_msg, has_valid_signature)

    def get_node_info(self, address: TCPAddress) -> NodeInfo:
        """Best effort node info getter."""
        return self.network_members.get(address, NodeInfo(address, None, None))
