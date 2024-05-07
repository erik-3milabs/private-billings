import socket
from socketserver import TCPServer
from threading import Thread
from time import sleep
from src.private_billing import BillingServer, BillingServerDataStore
from src.private_billing.messages import BootMessage, Message, WelcomeMessage
from src.private_billing.server import MessageSender, Target, MarketConfig


class TestBilling:

    def mock_operator(
        self,
        sock: socket.socket,
        resp: WelcomeMessage,
    ):
        sock.listen(1)
        conn, sender = sock.accept()
        print(f"accepted conn from {sender}")
        with conn:
            print(f"receiving message...")
            msg = MessageSender._receive(conn)
            print(f"received {msg}")

            resp.billing_server.address = sender

            print(f"sending response {resp}")
            MessageSender._send(conn, resp)
            print(f"sent response")

    def trigger_thread(self, msg: Message, target: Target):
        """
        Contact an address to send a message

        :param msg: message to
        """
        # Allow receiver startup to happen
        sleep(0.1)

        # Send message
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as trigger:
            trigger.connect(target.address)
            MessageSender._send(trigger, msg)
            response = MessageSender._receive(trigger)
            assert isinstance(response, WelcomeMessage)

    def test_registration(self):

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as operator:
            operator.bind(("localhost", 0))
            operator_address = operator.getsockname()
            print("operator is live on", operator_address)

            # Test settings
            billing_id = 42
            mc = MarketConfig(*operator_address, 5555, 5554)
            resp = WelcomeMessage(
                billing_id,
                Target(6, None),  # address to be set by the market operator mock
                [
                    Target(1, ("localhost", mc.peer_port)),
                    Target(2, ("localhost", mc.peer_port)),
                ],
                1024,
            )

            # Start operator mock
            operator_thread = Thread(target=self.mock_operator, args=(operator, resp))
            operator_thread.start()

            # Prepare trigger

            # Start
            billing_address = "localhost", 0
            with TCPServer(billing_address, BillingServer) as server:
                billing_address = server.server_address
                billing_server = Target(None, billing_address)

                # Setup trigger
                trigger_msg = BootMessage(mc)
                trigger_thread = Thread(
                    target=self.trigger_thread, args=(trigger_msg, billing_server)
                )
                trigger_thread.start()

                # Handle
                server.handle_request()

            operator_thread.join()

            # Check data store is updated
            bsds = BillingServerDataStore()
            assert bsds.id == billing_id
            for peer in resp.peers:
                assert peer in bsds.participants.values()
