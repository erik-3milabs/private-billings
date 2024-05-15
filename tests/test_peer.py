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
    def __init__(
        self, response_address: Tuple[str, int], data_store: PeerDataStore = None
    ) -> None:
        """Cutting away communication components."""
        server_mock = Namespace(server_address=response_address)
        super().__init__(None, None, server_mock)

        # Store responses and sent messages
        if not data_store:
            data_store = PeerDataStore()
        data_store.__replies__ = []
        data_store.__sent__ = []
        self.server.data = data_store

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


class TestPeer:

    def test_handle_registration(self):
        # Test settings
        sender = Target(0, ("Sender address", 1000))
        mc = MarketConfig("localhost", 5555, 5554, 5553)
        billing_server = Target(77, sender.address)
        welcome = WelcomeMessage(
            6,
            billing_server,
            [
                Target(1, ("localhost", mc.peer_port)),
                Target(2, ("localhost", mc.peer_port)),
            ],
            1024,
        )
        seed = SeedMessage(0, 12345)
        server_info = NewMemberMessage(billing_server, UserType.SERVER, "public key")

        # Mock some communication elements of BillingServer to keep this a unit test
        class MockedPeerServer(BasePeerMock):
            def send(cls, msg: Message, target: Target):
                super().send(msg, target)

                # Return a welcome message (expected behaviour from market operator)
                if isinstance(msg, HelloMessage):
                    return welcome

                if isinstance(msg, SeedMessage):
                    return seed
                
                if isinstance(msg, NewMemberMessage):
                    return server_info

        # Test input
        boot = BootMessage(mc)

        # Execute test
        response_address = ("some_address", "some_port")
        peer = MockedPeerServer(response_address)
        peer.handle_boot(boot, sender)

        # Check data store is updated accordingly
        pds = peer.server.data
        assert pds.id == welcome.id
        assert pds.hc != None
        assert pds.billing_server == billing_server
        assert pds.peers[1] == welcome.peers[0]
        assert pds.peers[2] == welcome.peers[1]

        # Check a message was replied
        assert len(peer._replies) == 1
        response = peer._replies[0]
        assert response == welcome

        # Check four messages were sent
        assert len(peer._sent) == 4
        first, second, third, fourth = peer._sent

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

        # the fourth is to the billing server
        msg, target = fourth
        assert isinstance(msg, NewMemberMessage)
        assert msg.new_member == Target(welcome.id, response_address)
        assert msg.member_type == UserType.CLIENT
        
        # Check public key was recorded
        assert pds.server_public_key == server_info.public_key

    def test_handle_new_peer(self):
        # Test input
        new_peer = Target(77, ("new peer address", "new peer port"))
        seed_msg = SeedMessage(77, 1234)

        # Execute test
        response_address = ("another address", "another port")
        peer = BasePeerMock(response_address)
        peer.handle_receive_seed(seed_msg, new_peer)

        # Check data store is updated accordingly
        pds = peer.server.data
        assert pds.peers[new_peer.id] == new_peer

        # Check a no-reply was returned
        assert len(peer._replies) == 1
        response = peer._replies[0]
        assert isinstance(response, SeedMessage)

        # Check no messages were sent
        assert len(peer._sent) == 0

    def test_handle_new_server(self):
        # Test input
        billing_server = Target(None, ("some address", "some port"))
        new_server = Target(77, ("new server address", "new server port"))
        new_member = NewMemberMessage(new_server, UserType.SERVER)

        # Execute test
        response_address = ("another address", "another port")
        peer = BasePeerMock(response_address)
        peer.handle_new_member(new_member, billing_server)

        # Check data store is updated accordingly
        pds = peer.server.data
        assert pds.billing_server == new_server

        # Check a no-reply was returned
        assert len(peer._replies) == 1
        response = peer._replies[0]
        assert response == ""

        # Check no messages were sent
        assert len(peer._sent) == 0

    def test_handle_receive_seed(self):
        # Test input
        peer = Target(77, ("some address", "some port"))
        new_seed = SeedMessage(77, 5555)

        # Execute test
        response_address = ("another address", "another port")
        peer_server = BasePeerMock(response_address)
        peer_server.handle_receive_seed(new_seed, peer)

        # Check data store is updated accordingly
        pds = peer_server.server.data
        assert pds.mg.has_foreign_seed_from_peer(peer.id)

        # Check a no-reply was returned
        assert len(peer_server._replies) == 1
        response = peer_server._replies[0]
        assert isinstance(response, SeedMessage)
        assert response.seed != None

        # Check no messages were sent
        assert len(peer_server._sent) == 0

    def test_handle_receive_bill(self):
        class HiddenBillMock(HiddenBill):
            def reveal(self, hc: HidingContext):
                return Bill(self.cycle_id, self.hidden_bill, self.hidden_reward)

        # Test input
        billing_server = Target(77, ("some address", "some port"))
        bill = BillMessage(HiddenBillMock(0, "test1", "test2"), None)

        # Execute test
        response_address = ("another address", "another port")
        peer_server = BasePeerMock(response_address)
        peer_server.handle_receive_bill(bill, billing_server)

        # Check data store is updated accordingly
        pds = peer_server.server.data
        assert Bill(0, "test1", "test2") in pds.bills.values()

        # Check a no-reply was returned
        assert len(peer_server._replies) == 1
        response = peer_server._replies[0]
        assert response == ""

        # Check no messages were sent
        assert len(peer_server._sent) == 0

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
        pds = peer.server.data
        assert cyc in pds.context.values()

        # Check a no-reply was returned
        assert len(peer._replies) == 1
        response = peer._replies[0]
        assert response == ""

        # Check no messages were sent
        assert len(peer._sent) == 0
