from argparse import Namespace
from src.private_billing.server.message_handler import ADDRESS
from src.private_billing.core import HiddenBill, Data
from src.private_billing import BillingServer, BillingServerDataStore
from src.private_billing.messages import (
    BillMessage,
    BootMessage,
    HiddenDataMessage,
    HelloMessage,
    Message,
    NewMemberMessage,
    UserType,
    WelcomeMessage,
)
from src.private_billing.server import Target, MarketConfig


class BaseBillingServerMock(BillingServer):
    def __init__(self, response_address: ADDRESS) -> None:
        """Cutting away communication components."""
        server_mock = Namespace(server_address=response_address)
        super().__init__(None, None, server_mock)

        # Store responses and sent messages
        mods = BillingServerDataStore()
        mods.__replies__ = []
        mods.__sent__ = []

    def handle(self) -> None:
        """Not handling anything in this test"""
        pass

    def send(self, message: Message, target: Target):
        self.data.__sent__.append((message, target))

    def reply(self, msg: Message) -> None:
        self.data.__replies__.append(msg)

    @property
    def _sent(self):
        return self.data.__sent__

    @property
    def _replies(self):
        return self.data.__replies__


def clean_datastore(func, *args, **kwargs):
    """
    Used to indicate this handler will not provide a response.
    Makes sure to close the socket on the other side.
    """

    def wrapper(self, *args, **kwargs):
        BillingServerDataStore().__init__()  # reset datastore before a test
        func(self, *args, **kwargs)

    return wrapper


class TestBilling:

    @clean_datastore
    def test_registration(self):
        # Test settings
        sender = Target(0, ("Sender address", 1000))
        mc = MarketConfig("localhost", 5555, 5554, 5553)
        welcome = WelcomeMessage(
            6,
            Target(6, sender.address),
            [
                Target(1, ("localhost", mc.peer_port)),
                Target(2, ("localhost", mc.peer_port)),
            ],
            1024,
        )

        # Mock some communication elements of BillingServer to keep this a unit test
        class MockedBillingServer(BaseBillingServerMock):
            def send(cls, message: Message, target: Target):
                # Test the billing server sends a HelloMessage ...
                assert isinstance(message, HelloMessage)

                # ... to the marker operator.
                assert target == Target(None, (mc.market_host, mc.market_port))

                # Return a welcome message (expected behaviour from market operator)
                return welcome

        # Test input
        boot = BootMessage(mc)

        # Execute test
        response_address = ("some_address", "some_port")
        server = MockedBillingServer(response_address)
        server.handle_boot(boot, sender)

        # Check data store is updated accordingly
        bsds = BillingServerDataStore()
        assert bsds.id == welcome.id
        for peer in welcome.peers:
            assert peer in bsds.participants.values()

        # Check a message was replied
        assert len(server._replies) == 1
        response = server._replies[0]
        assert response == welcome

    @clean_datastore
    def test_handle_new_member_client(self):
        class MockedBillingServer(BaseBillingServerMock):
            def reply(self, msg: Message) -> None:
                """Test reply message"""
                # Should send a "no-reply"
                assert msg == ""

        # Test input
        new_member = Target(5, ("new member address", 1234))
        new_member_msg = NewMemberMessage(new_member, UserType.CLIENT)
        sender = Target(0, ("marker operator address", 2345))

        # Execute test
        response_address = ("some_address", "some_port")
        MockedBillingServer(response_address).handle_new_member(new_member_msg, sender)

        # Check new member is included in data store
        bsds = BillingServerDataStore()
        assert new_member in bsds.participants.values()

    @clean_datastore
    def test_handle_new_member_server(self):
        # Test input
        new_server = Target(5, ("new server address", 1234))
        new_server_msg = NewMemberMessage(new_server, UserType.SERVER)
        sender = Target(0, ("marker operator address", 2345))

        # Execute test
        response_address = ("some_address", "some_port")
        server = BaseBillingServerMock(response_address)
        server.handle_new_member(new_server_msg, sender)

        # Check new server is NOT included in data store
        bsds = BillingServerDataStore()
        assert new_server not in bsds.participants.values()

        # Check a no-reply was sent
        assert len(server._replies) == 1
        response = server._replies[0]
        assert response == ""

    @clean_datastore
    def test_handle_receive_data(self):
        # Mock
        client_id = 5
        bsds = BillingServerDataStore()
        bsds.shared_biller.clients.add(client_id)

        # Test input
        data = Data(0, 1, None, None)
        data_msg = HiddenDataMessage(data)
        sender = Target(0, ("marker operator address", 2345))

        # Execute test
        response_address = ("some_address", "some_port")
        server = BaseBillingServerMock(response_address)
        server.handle_receive_data(data_msg, sender)

        # Check data is stored under the right id
        bsds = BillingServerDataStore()
        assert bsds.shared_biller.client_data[data.cycle_id][data.client] == data

        # Check a no-reply was sent
        assert len(server._replies) == 1
        response = server._replies[0]
        assert response == ""

    @clean_datastore
    def test_handle_receive_data_starts_billing_when_ready(self):
        # Mock
        cycle_id, client_id = 0, 5
        bsds = BillingServerDataStore()
        bsds.shared_biller.include_client(client_id)
        bsds.run_billing_count = 0

        class MockedBillingServer(BaseBillingServerMock):
            def run_billing(self, cycle_id: int) -> None:
                # should be called for cycle_1
                assert cycle_id == 0
                self.data.run_billing_count += 1

        # Test input
        data = Data(client_id, cycle_id, None, None)
        data_msg = HiddenDataMessage(data)
        sender = Target(0, ("marker operator address", 2345))

        # Execute test
        response_address = ("some_address", "some_port")
        server = MockedBillingServer(response_address)
        server.handle_receive_data(data_msg, sender)

        # Check run_billing is called
        assert bsds.run_billing_count == 1

        # Check a no-reply was sent
        assert len(server._replies) == 1
        response = server._replies[0]
        assert response == ""

    @clean_datastore
    def test_run_billing(self):
        # Mock
        cycle_id, client_id = 0, 5
        bill_cycle_id = 555

        # Test input
        data = Data(client_id, cycle_id, None, None)

        # Seed data store
        bsds = BillingServerDataStore()
        bsds.participants = {client_id: Target(client_id, None)}
        bsds.shared_biller.include_client(client_id)
        bsds.shared_biller.record_data(data)

        # Mock sharedbilling compute bills
        def compute_bills_mock(cid):
            assert cid == cycle_id
            return {client_id: HiddenBill(bill_cycle_id, "test1", "test2")}

        bsds.shared_biller.compute_bills = compute_bills_mock

        # Execute test
        response_address = ("some_address", "some_port")
        server = BaseBillingServerMock(response_address)
        server.run_billing(cycle_id)

        # Check bill was sent
        assert len(server._sent) == 1
        msg, sender = server._sent[0]
        assert isinstance(msg, BillMessage)
        bill = msg.bill
        assert bill.cycle_id == bill_cycle_id
        assert bill.hidden_bill == "test1"
        assert bill.hidden_reward == "test2"

    @clean_datastore
    def test_register_client(self):
        # Mock
        client = Target(5, None)

        # Execute test
        response_address = ("some_address", "some_port")
        BaseBillingServerMock(response_address).record_client(client)

        # Check client is stored as participant
        bsds = BillingServerDataStore()
        assert bsds.participants[client.id] == client

        # Check client is stored with the biller
        assert client.id in bsds.shared_biller.clients
