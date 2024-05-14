from argparse import Namespace
from typing import Tuple
from src.private_billing.core import (
    Bill,
    CycleContext,
    HiddenBill,
    HidingContext,
    vector,
)
from src.private_billing import Peer, PeerDataStore
from src.private_billing.messages import (
    BillMessage,
    BootMessage,
    ContextMessage,
    HelloMessage,
    Message,
    NewMemberMessage,
    SeedMessage,
    UserType,
    WelcomeMessage,
)
from src.private_billing.server import Target, MarketConfig


class BasePeerMock(Peer):
    def __init__(self, response_address: Tuple[str, int]) -> None:
        """Cutting away communication components."""
        server_mock = Namespace(server_address=response_address)
        super().__init__(None, None, server_mock)

        # Store responses and sent messages
        pds = PeerDataStore()
        pds.__replies__ = []
        pds.__sent__ = []

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
        PeerDataStore().__init__()  # reset datastore before a test
        func(self, *args, **kwargs)

    return wrapper


class TestPeer:

    @clean_datastore
    def test_handle_registration(self):
        # Test settings
        sender = Target(0, ("Sender address", 1000))
        mc = MarketConfig("localhost", 5555, 5554, 5553)
        billing_server = Target(77, sender.address),
        welcome = WelcomeMessage(
            6,
            billing_server
            [
                Target(1, ("localhost", mc.peer_port)),
                Target(2, ("localhost", mc.peer_port)),
            ],
            1024,
        )

        # Mock some communication elements of BillingServer to keep this a unit test
        class MockedPeerServer(BasePeerMock):
            def send(cls, message: Message, target: Target):
                super().send(message, target)
                # Return a welcome message (expected behaviour from market operator)
                return welcome

        # Test input
        boot = BootMessage(mc)

        # Execute test
        response_address = ("some_address", "some_port")
        peer = MockedPeerServer(response_address)
        peer.handle_boot(boot, sender)

        # Check data store is updated accordingly
        pds = PeerDataStore()
        assert pds.id == welcome.id
        assert pds.hc != None
        assert pds.billing_server == billing_server
        assert pds.peers[1] == welcome.peers[0]
        assert pds.peers[2] == welcome.peers[1]

        # Check a message was replied
        assert len(peer._replies) == 1
        response = peer._replies[0]
        assert response == welcome

        # Check three messages were sent
        assert len(peer._sent) == 3
        first, second, third = peer._sent

        # first message should have been sent to the market operator
        msg, target = first
        assert msg == HelloMessage(UserType.CLIENT, response_address=response_address)
        market_operator = Target(None, (mc.market_host, mc.market_port))
        assert target == market_operator

        # second and third messages are seed messages
        msg, target = second
        assert isinstance(msg, SeedMessage)
        assert msg.seed != None
        assert target == welcome.peers[0]

        msg, target = third
        assert isinstance(msg, SeedMessage)
        assert msg.seed != None
        assert target == welcome.peers[1]

    @clean_datastore
    def test_handle_new_peer(self):
        # Test input
        market_operator = Target(None, ("some address", "some port"))
        new_peer = Target(77, ("new peer address", "new peer port"))
        new_member = NewMemberMessage(new_peer, UserType.CLIENT)

        # Execute test
        response_address = ("another address", "another port")
        peer = BasePeerMock(response_address)
        peer.handle_new_member(new_member, market_operator)

        # Check data store is updated accordingly
        pds = PeerDataStore()
        assert pds.peers[new_peer.id] == new_peer

        # Check a no-reply was returned
        assert len(peer._replies) == 1
        response = peer._replies[0]
        assert response == ""

        # Check a message was sent to that peer
        assert len(peer._sent) == 1
        msg, target = peer._sent[0]
        assert target == new_peer
        assert isinstance(msg, SeedMessage)
        assert msg.seed != None

    @clean_datastore
    def test_handle_new_server(self):
        # Test input
        market_operator = Target(None, ("some address", "some port"))
        new_server = Target(77, ("new server address", "new server port"))
        new_member = NewMemberMessage(new_server, UserType.SERVER)

        # Execute test
        response_address = ("another address", "another port")
        peer = BasePeerMock(response_address)
        peer.handle_new_member(new_member, market_operator)

        # Check data store is updated accordingly
        pds = PeerDataStore()
        assert pds.billing_server == new_server

        # Check a no-reply was returned
        assert len(peer._replies) == 1
        response = peer._replies[0]
        assert response == ""

        # Check no messages were sent
        assert len(peer._sent) == 0

    @clean_datastore
    def test_handle_receive_seed(self):
        # Test input
        peer = Target(77, ("some address", "some port"))
        new_seed = SeedMessage(5555)

        # Execute test
        response_address = ("another address", "another port")
        peer_server = BasePeerMock(response_address)
        peer_server.handle_receive_seed(new_seed, peer)

        # Check data store is updated accordingly
        pds = PeerDataStore()
        assert pds.mg.has_foreign_seed_from_peer(peer.id)

        # Check a no-reply was returned
        assert len(peer_server._replies) == 1
        response = peer_server._replies[0]
        assert response == ""

        # Check no messages were sent
        assert len(peer_server._sent) == 0

    @clean_datastore
    def test_handle_receive_bill(self):
        class HiddenBillMock(HiddenBill):
            def reveal(self, hc: HidingContext):
                return Bill(self.cycle_id, self.hidden_bill, self.hidden_reward)

        # Test input
        billing_server = Target(77, ("some address", "some port"))
        bill = BillMessage(HiddenBillMock(0, "test1", "test2"))

        # Execute test
        response_address = ("another address", "another port")
        peer_server = BasePeerMock(response_address)
        peer_server.handle_receive_bill(bill, billing_server)

        # Check data store is updated accordingly
        pds = PeerDataStore()
        assert Bill(0, "test1", "test2") in pds.bills.values()

        # Check a no-reply was returned
        assert len(peer_server._replies) == 1
        response = peer_server._replies[0]
        assert response == ""

        # Check no messages were sent
        assert len(peer_server._sent) == 0

    @clean_datastore
    def test_handle_receive_context(self):
        # Test input
        market_operator = Target(None, ("some address", "some port"))
        cyc = CycleContext(
            0, 1024, vector.new(1024), vector.new(1024), vector.new(1024)
        )
        context_msg = ContextMessage(cyc)

        # Execute test
        response_address = ("another address", "another port")
        peer = BasePeerMock(response_address)
        peer.handle_receive_context(context_msg, market_operator)

        # Check data store is updated accordingly
        pds = PeerDataStore()
        assert cyc in pds.context.values()

        # Check a no-reply was returned
        assert len(peer._replies) == 1
        response = peer._replies[0]
        assert response == ""

        # Check no messages were sent
        assert len(peer._sent) == 0
