import socket
from src.private_billing.core import (
    Data,
    HiddenData,
    HidingContext,
    Int64ToFloatConvertor,
    SharedMaskGenerator,
    vector,
)
from src.private_billing.server import MessageSender, Target
from src.private_billing.messages import HiddenDataMessage, WelcomeMessage
from tests.core.tools import are_equal_ciphertexts
from threading import Thread
from time import sleep


class TestMessageSenderEncoding:

    def test_encode_decode_is_identity(self):
        """Test that a decoded encoding is the original value"""
        msg = WelcomeMessage(
            0,
            Target(1, ("localhost", 5555)),
            [Target(2, ("172.168.192.255", 3333))],
            1024,
        )
        enc = MessageSender.encode(msg)
        dec = MessageSender.decode(enc)
        assert msg == dec


class TestMessageSender:

    def test_send_msg(self):
        msg = WelcomeMessage(
            0,
            Target(1, ("localhost", 5555)),
            [Target(2, ("172.168.192.255", 3333))],
            1024,
        )

        def send(dest):
            sleep(0.1)
            MessageSender.send(msg, dest)

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("localhost", 0))
            address = s.getsockname()
            print(f"bound to {address}")

            dest = Target(0, address)
            thread = Thread(target=send, args=(dest,))
            thread.start()

            s.listen()

            conn, _ = s.accept()
            with conn:
                rcvd_msg = MessageSender._receive(conn)
                print(rcvd_msg)

            sleep(0.5)
            thread.join()

        assert msg == rcvd_msg

    def test_send_msg_large(self):
        data = Data(
            0,
            1,
            vector.new(2048, 1),
            vector.new(2048, 2),
        )
        msg = HiddenDataMessage(data)

        def send(dest):
            sleep(0.1)
            MessageSender.send(msg, dest)

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("localhost", 0))
            address = s.getsockname()
            print(f"bound to {address}")

            dest = Target(0, address)
            thread = Thread(target=send, args=(dest,))
            thread.start()

            s.listen()

            conn, _ = s.accept()
            with conn:
                rcvd_msg = MessageSender._receive(conn)

            thread.join()

        assert rcvd_msg == msg


class TestSendIntegration:
    def test_send_large_message(self):
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
        msg = HiddenDataMessage(hd)

        def send(dest):
            sleep(0.1)
            MessageSender.send(msg, dest)

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("localhost", 0))
            address = s.getsockname()
            print(f"bound to {address}")

            dest = Target(0, address)
            thread = Thread(target=send, args=(dest,))
            thread.start()

            s.listen()

            conn, _ = s.accept()
            with conn:
                rcvd_msg = MessageSender._receive(conn)

            thread.join()

        rcvd_hd: HiddenData = rcvd_msg.data

        # Check plaintext
        assert rcvd_hd.client == hd.client
        assert rcvd_hd.cycle_id == hd.cycle_id
        assert rcvd_hd.masked_individual_deviations == hd.masked_individual_deviations
        assert rcvd_hd.masked_p2p_consumer_flags == hd.masked_p2p_consumer_flags
        assert rcvd_hd.masked_p2p_producer_flags == hd.masked_p2p_producer_flags

        # Check ciphertexts are identical
        assert are_equal_ciphertexts(rcvd_hd.consumptions, hd.consumptions, hc)
        assert are_equal_ciphertexts(rcvd_hd.supplies, hd.supplies, hc)
        assert are_equal_ciphertexts(rcvd_hd.accepted_consumer_flags, hd.accepted_consumer_flags, hc)
        assert are_equal_ciphertexts(rcvd_hd.accepted_producer_flags, hd.accepted_producer_flags, hc)
        assert are_equal_ciphertexts(
            rcvd_hd.positive_deviation_flags, hd.positive_deviation_flags, hc
        )
