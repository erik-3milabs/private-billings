import random
import pytest
from src.private_billing.network import NodeInfo, NoValidSignatureException
from src.private_billing.server import TCPAddress, PickleEncoder, Signer
from src.private_billing.core import Bill
from src.private_billing import CoreServer
from src.private_billing.messages import (
    ConnectMessage,
    HiddenBillMessage,
    Message,
    SeedMessage,
    SignedMessage,
    UserType,
)
from tests.core.tools import HiddenBillMock


class BaseCoreServerMock(CoreServer):
    def __init__(self, response_address: TCPAddress) -> None:
        super().__init__(response_address)

        # Store responses and sent messages
        self.__replies__ = []
        self.__sent__ = []

    def _execute(self, handler, *args) -> None:
        handler(*args)

    def send(self, message: Message, target: NodeInfo):
        self.__sent__.append((message, target))

    def _reply(self, msg: Message) -> None:
        pass

    @property
    def _sent(self):
        return self.__sent__


class TestCoreServer:

    def random_node(self, role=UserType.CORE):
        address = TCPAddress("localhost", random.randint(500, 1000))
        signer = Signer()
        pk = signer.get_transferable_public_key()
        info = NodeInfo(address, pk, role)
        return address, signer, pk, info

    def test_init(self):
        response_address = TCPAddress("someaddress", 1234)
        peer = BaseCoreServerMock(response_address)

        _self = peer.network_members[response_address]
        assert _self
        assert _self.address == response_address
        assert _self.role == UserType.CORE

    @pytest.mark.parametrize("role", (UserType.EDGE, UserType.CORE))
    def test_handle_connect(self, role):
        # Define third party
        other_address, _, other_pk, other_node = self.random_node(role)

        # Define connecting party
        address, _, pk, node = self.random_node(role)
        network_state = {address: node, other_address: other_node}
        billing_state = {"cycle_length": 1000}
        msg = ConnectMessage(address, pk, role, network_state, billing_state)

        # Handle message
        response_address = TCPAddress("someaddress", 1234)
        peer = BaseCoreServerMock(response_address)
        peer.handle_connect(msg, other_node)

        # Check state is properly updated
        assert peer.network_members[address] == node
        assert peer.network_members[other_address] == other_node

        # Check that peer sent connect messages to all parties
        connect_msgs = list(
            filter(lambda x: isinstance(x[0], ConnectMessage), peer._sent)
        )
        assert any(filter(lambda x: x[1] == address, connect_msgs))
        assert any(filter(lambda x: x[1] == other_address, connect_msgs))

        # Check that peer sent seed messages to the sender, if it is a CORE party
        seed_msgs = list(filter(lambda x: isinstance(x[0], SeedMessage), peer._sent))
        print(seed_msgs)
        if role == UserType.CORE:
            assert any(filter(lambda x: x[1].address == other_address, seed_msgs))

    def test_handle_seed_requires_signature(self):        
        # Create target
        msg = SeedMessage(None, 5)
        peer = BaseCoreServerMock(None)

        # Handle message
        with pytest.raises(NoValidSignatureException):
            peer._handle(msg)

    def test_handle_seed(self):
        # Define sending party
        seed = 123456789101010
        address, signer, _, sender = self.random_node(UserType.CORE)
        seed_msg = SeedMessage(address, seed)
        seed_msg_bytes = PickleEncoder.encode(seed_msg)
        sgn = signer.sign(seed_msg_bytes)
        msg = SignedMessage(seed_msg_bytes, sgn)

        # Create target
        response_address = TCPAddress("someaddress", 1234)
        peer = BaseCoreServerMock(response_address)

        # Add sender to internal state
        peer.network_members[address] = sender

        # Handle message
        peer._handle(msg)

        # Check state is properly updated
        assert peer.mg.foreign_seeds[sender.id] == seed

        # Check that peer sent seed messages to the sender
        assert len(peer._sent) == 1
        response, target = peer._sent[0]
        assert isinstance(response, SeedMessage)
        assert response.seed != None
        assert target == sender

    def test_handle_receive_bill_requires_signature(self):        
        # Create target
        msg = HiddenBillMessage(None, None)
        peer = BaseCoreServerMock(None)

        # Handle message
        with pytest.raises(NoValidSignatureException):
            peer._handle(msg)

    def test_handle_receive_bill(self):
        # Define sending party
        signer = Signer()
        pk = signer.get_transferable_public_key()
        address = TCPAddress("localhost", 2345)
        sender = NodeInfo(address, pk, UserType.CORE)
        hidden_bill = HiddenBillMock(0, "test1", "test2")
        bill_msg = HiddenBillMessage(address, hidden_bill)
        bill_msg_bytes = PickleEncoder.encode(bill_msg)
        sgn = signer.sign(bill_msg_bytes)
        signed_msg = SignedMessage(bill_msg_bytes, sgn)

        class CoreMock(BaseCoreServerMock):
            def verify_signature(self, msg):
                self.verify_called = True
                return super().verify_signature(msg)

        # Setup server
        response_address = ("another address", "another port")
        peer_server = CoreMock(response_address)
        peer_server.network_members[address] = sender  # register

        # Handle
        peer_server._handle(signed_msg)

        # Check data store is updated accordingly
        assert peer_server.bills[0] == Bill(0, "test1", "test2")

        # Check no messages were sent
        assert len(peer_server._sent) == 0

        # Check signature is verified
        assert peer_server.verify_called
