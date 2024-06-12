import random
import pytest
from private_billing.core import CycleID
from src.private_billing.core.cycle import CycleContext
from src.private_billing.core.data import Data
from src.private_billing.core.hidden_data import HiddenData
from src.private_billing.core.hiding import HidingContext
from src.private_billing.core.masking import Int64ToFloatConvertor, SharedMaskGenerator
from src.private_billing.core.utils import vector
from src.private_billing.network import NoValidSignatureException, NodeInfo
from src.private_billing.server import TCPAddress, PickleEncoder, Signer
from src.private_billing.core import Bill
from src.private_billing import EdgeServer
from src.private_billing.messages import (
    ConnectMessage,
    ContextMessage,
    HiddenBillMessage,
    HiddenDataMessage,
    Message,
    SeedMessage,
    SignedMessage,
    UserType,
)
from tests.core.tools import HiddenBillMock


class BaseEdgeServerMock(EdgeServer):
    def __init__(self, response_address: TCPAddress, cycle_length: int) -> None:
        super().__init__(response_address, cycle_length)

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


class TestEdgeServer:

    def random_node(self, role=UserType.CORE):
        address = TCPAddress("localhost", random.randint(500, 1000))
        signer = Signer()
        pk = signer.get_transferable_public_key()
        info = NodeInfo(address, pk, role)
        return address, signer, pk, info

    def test_init(self):
        response_address = TCPAddress("someaddress", 1234)
        edge = BaseEdgeServerMock(response_address, 1024)

        _self = edge.network_members[response_address]
        assert _self
        assert _self.address == response_address
        assert _self.role == UserType.EDGE

    def test_register_node(self):
        response_address = TCPAddress("someaddress", 1234)
        edge = BaseEdgeServerMock(response_address, 1024)

        node = self.random_node()[3]
        edge.register_node(node)

        assert node.id in edge.shared_biller.clients

    def test_handle_context_data(self):
        class EdgeServerMock(BaseEdgeServerMock):
            def try_run_billing(self, msg):
                self.try_run_billing_called = True
                return super().try_run_billing(msg)

        # Create edge
        response_address = TCPAddress("someaddress", 1234)
        edge = EdgeServerMock(response_address, 1024)

        # Register some nodes
        for _ in range(3):
            address, _, _, node = self.random_node()
            edge.network_members[address] = node

        # Create ContextData message
        cyclen = 672
        cyc = CycleContext(
            0,
            cyclen,
            vector.new(cyclen, 0.21),
            vector.new(cyclen, 0.05),
            vector.new(cyclen, 0.11),
        )
        msg = ContextMessage(None, cyc)

        # Handle message
        edge._handle(msg)

        # Test state updates
        assert cyc.cycle_id in edge.shared_biller.cycle_contexts
        assert edge.try_run_billing_called

        # Check context data is broadcast
        sent_context_msg = list(
            filter(lambda x: isinstance(x[0], ContextMessage), edge._sent)
        )
        assert len(sent_context_msg) == 3

    def test_handle_hidden_data_requires_signature(self):
        # Create target
        msg = HiddenDataMessage(None, None)
        edge = BaseEdgeServerMock(None, None)

        # Handle message
        with pytest.raises(NoValidSignatureException):
            edge._handle(msg)

    def test_handle_hidden_data(self):
        class EdgeServerMock(BaseEdgeServerMock):
            def try_run_billing(self, msg):
                self.try_run_billing_called = True
                return super().try_run_billing(msg)

        # Create edge
        response_address = TCPAddress("someaddress", 1234)
        edge = EdgeServerMock(response_address, 1024)

        # Register some nodes
        for _ in range(3):
            address, signer, _, node = self.random_node()
            edge.network_members[address] = node

        # Create HiddenData message
        hd = HiddenData(0, 0, None, None, None, None, None, None, None, None, None)
        msg = HiddenDataMessage(address, hd)
        msg_bytes = PickleEncoder.encode(msg)
        sgn = signer.sign(msg_bytes)
        msg = SignedMessage(msg_bytes, sgn)

        # Handle message
        edge._handle(msg)

        # Test state updates
        assert edge.shared_biller.client_data[hd.cycle_id][hd.client] == hd
        assert edge.try_run_billing_called

    def test_sends_bills(self):
        class EdgeServerMock(BaseEdgeServerMock):
            def __init__(self, response_address: TCPAddress, cycle_length: CycleID) -> None:
                super().__init__(response_address, cycle_length)
                self.try_run_billing_called = 0
                self.run_billing_called = False

            def try_run_billing(self, cycle_id: int) -> None:
                self.try_run_billing_called += 1
                return super().try_run_billing(cycle_id)

            def run_billing(self, msg):
                self.run_billing_called = True
                return super().run_billing(msg)

        # Create edge
        response_address = TCPAddress("someaddress", 1234)
        edge = EdgeServerMock(response_address, 1024)

        # Register some nodes
        cyclen = 672
        mg = SharedMaskGenerator(Int64ToFloatConvertor(4, 6))
        for _ in range(3):
            address, signer, _, node = self.random_node()
            edge.register_node(node)

            # Create HiddenData message
            data = Data(node.id, 0, vector.new(cyclen, 5), vector.new(cyclen, 5))
            hc = HidingContext(cyclen, mg)
            hd = data.hide(hc)
            msg = HiddenDataMessage(address, hd)
            msg_bytes = PickleEncoder.encode(msg)
            sgn = signer.sign(msg_bytes)
            msg = SignedMessage(msg_bytes, sgn)

            # Handle message
            edge._handle(msg)

        # Send context
        cyc = CycleContext(
            0,
            cyclen,
            vector.new(cyclen, 0.21),
            vector.new(cyclen, 0.05),
            vector.new(cyclen, 0.11),
        )
        msg = ContextMessage(None, cyc)
        edge._handle(msg)

        # Test state updates
        assert edge.try_run_billing_called == 4
        assert edge.run_billing_called

        # Check bills are sent out
        sent_bill_msg = list(
            filter(lambda x: isinstance(x[0], HiddenBillMessage), edge._sent)
        )
        assert len(sent_bill_msg) == 3
