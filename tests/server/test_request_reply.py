# import socket
import pytest
from src.private_billing.messages import DataMessage, HiddenDataMessage
from src.private_billing.core import (
    Data,
    HiddenData,
    HidingContext,
    Int64ToFloatConvertor,
    SharedMaskGenerator,
    vector,
)
from src.private_billing.server import (
    RequestReplyServer,
    TCPAddress,
    Message,
    PickleEncoder,
)
from tests.core.tools import are_equal_ciphertexts
from threading import Thread



class TestTCPAddress:

    def test_str(self):
        address = TCPAddress("hello", 5555)
        assert isinstance(str(address), str)

    def test_hash(self):
        address = TCPAddress("hello", 5555)
        assert isinstance(hash(address), int)

    def test_hash_is_consistent(self):
        address = TCPAddress("hello", 5555)
        hash1 = hash(address)
        hash2 = hash(address)
        assert hash1 == hash2


class TestRequestReplyServerTerminate:

    def test_terminate(self):
        server = RequestReplyServer(None)
        thread = Thread(target=server.start)
        thread.start()
        server.terminate()
        thread.join(3.0)
        assert not thread.is_alive()


class RequestReplyServerTester(RequestReplyServer):

    def __post_init__(self):
        super().__post_init__()
        self.messages = []

    def _handle(self, msg: Message) -> None:
        self.messages.append(msg)       
        self.reply("")


@pytest.fixture
def receiving_server():
    # start server
    server = RequestReplyServerTester(PickleEncoder)
    thread = Thread(target=server.start)
    thread.start()

    yield server, TCPAddress("localhost", 5555)

    # terminate server
    server.terminate()
    thread.join(3)


class TestRequestReplyServerSend:

    def test_send_msg(self, receiving_server):
        receiving_server, target = receiving_server
        
        # Setup sending server
        server = RequestReplyServerTester(PickleEncoder)

        # Send message
        msg = "hello!"
        server.send(msg, target)

        # Test is has arrived
        receiving_server.messages = [msg]

    def test_send_msg_large(self, receiving_server):
        receiving_server, target = receiving_server

        # Setup sending server
        sending_server = RequestReplyServerTester(PickleEncoder)

        # Send large message
        msg = DataMessage(
            None,
            Data(
                0,
                1,
                vector.new(2048, 1),
                vector.new(2048, 2),
            ),
        )
        sending_server.send(msg, target)

        # Test is has arrived
        receiving_server.messages = [msg]


class TestSendIntegration:
    def test_send_large_message(self, receiving_server):
        receiving_server, target = receiving_server

        # Setup sending server
        sending_server = RequestReplyServerTester(PickleEncoder)

        # Construct message
        cycle_length = 1024
        mg = SharedMaskGenerator(Int64ToFloatConvertor(4, 4))
        hc = HidingContext(cycle_length, mg)
        data = Data(
            0,
            1,
            vector.new(cycle_length, 1),
            vector.new(cycle_length, 2),
        )
        hd = data.hide(hc)
        hd.phc = None
        msg = HiddenDataMessage(None, hd)

        # Send message
        sending_server.send(msg, target)
        rcvd_hd: HiddenData = receiving_server.messages[0].data

        # Check plaintext
        assert rcvd_hd.client == hd.client
        assert rcvd_hd.cycle_id == hd.cycle_id
        assert rcvd_hd.masked_individual_deviations == hd.masked_individual_deviations
        assert rcvd_hd.masked_p2p_consumer_flags == hd.masked_p2p_consumer_flags
        assert rcvd_hd.masked_p2p_producer_flags == hd.masked_p2p_producer_flags

        # Check ciphertexts are identical
        assert are_equal_ciphertexts(rcvd_hd.consumptions, hd.consumptions, hc)
        assert are_equal_ciphertexts(rcvd_hd.supplies, hd.supplies, hc)
        assert are_equal_ciphertexts(
            rcvd_hd.accepted_consumer_flags, hd.accepted_consumer_flags, hc
        )
        assert are_equal_ciphertexts(
            rcvd_hd.accepted_producer_flags, hd.accepted_producer_flags, hc
        )
        assert are_equal_ciphertexts(
            rcvd_hd.positive_deviation_flags, hd.positive_deviation_flags, hc
        )
