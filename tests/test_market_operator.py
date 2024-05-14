from argparse import Namespace
from typing import Tuple
from src.private_billing import MarketOperator, MarketOperatorDataStore
from src.private_billing.messages import (
    ContextMessage,
    HelloMessage,
    Message,
    UserType,
    WelcomeMessage,
)
from src.private_billing.server import Target


class BaseMarketOperatorMock(MarketOperator):
    def __init__(
        self,
        response_address: Tuple[str, int],
        data_store: MarketOperatorDataStore = None,
    ) -> None:
        server_mock = Namespace(server_address=response_address)
        super().__init__(None, None, server_mock)

        # Store responses and sent messages
        if data_store == None:
            data_store = MarketOperatorDataStore()
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


class TestMarketOperator:

    def test_handle_hello_first_client(self):
        # Test input
        new_peer = Target(None, ("Sender address", 1000))
        peer_response_address = ("Sender address", 5555)
        hello = HelloMessage(UserType.CLIENT, peer_response_address)

        # Execute test
        operator = BaseMarketOperatorMock(peer_response_address)
        operator.handle_hello(hello, new_peer)

        # Check client was registered
        mods = operator.server.data
        assert mods.participants[peer_response_address] != None
        assert mods.participants[peer_response_address].id != None

        # Check response
        assert len(operator._replies) == 1
        response = operator._replies[0]
        assert isinstance(response, WelcomeMessage)
        assert response.id != None
        assert response.billing_server == None
        assert response.peers == []

        # Check no other messages are sent
        assert operator._sent == []

    def test_handle_hello_later_client(self):
        """Test handle_hello when other clients + server have previously registered."""
        existing_billing_server = Target(77, None)
        existing_peer = Target(55, ("192.168.5.24", 1234))

        # Setup test context
        mods = MarketOperatorDataStore()
        mods.billing_server = existing_billing_server
        mods.participants[existing_peer.address] = existing_peer

        # Test input
        new_peer = Target(None, ("Sender address", 1000))
        peer_response_address = ("Sender address", 5555)
        hello = HelloMessage(UserType.CLIENT, peer_response_address)

        # Execute test
        operator = BaseMarketOperatorMock(peer_response_address, mods)
        operator.handle_hello(hello, new_peer)

        # Check response includes peer and server information
        assert len(operator._replies) == 1
        response = operator._replies[0]
        assert isinstance(response, WelcomeMessage)
        assert response.id != None
        assert response.billing_server == mods.billing_server
        assert response.peers == [existing_peer]

        # Check previously registered peers + server are notified
        assert len(operator._sent) == 0

    def test_handle_hello_later_server(self):
        """Test handle_hello for a server, when other clients have previously registered."""
        # Setup test context
        mods = MarketOperatorDataStore()
        existing_peer = Target(55, ("192.168.5.24", 1234))
        mods.participants[existing_peer.address] = existing_peer

        # Test input
        server_response_address = ("Sender address", 5555)
        new_server = Target(None, ("Sender address", 1000))
        hello = HelloMessage(UserType.SERVER, server_response_address)

        # Execute test
        operator = BaseMarketOperatorMock(server_response_address, mods)
        operator.handle_hello(hello, new_server)

        # Check server was registered properly
        assert mods.billing_server.address == server_response_address
        assert mods.participants == {existing_peer.address: existing_peer}

        # Check response
        assert len(operator._replies) == 1
        response = operator._replies[0]
        assert isinstance(response, WelcomeMessage)
        assert response.id != None
        assert response.billing_server.address == server_response_address
        assert response.peers == [existing_peer]

        # Check previously registered peers are notified
        assert len(mods.__sent__) == 1
        msg, target = mods.__sent__[0]
        assert target == existing_peer
        assert msg.new_member.id == response.id
        assert msg.new_member.address == server_response_address
        assert msg.member_type == UserType.SERVER

    def test_handle_distribute_cycle_context(self):
        existing_billing_server = Target(77, None)
        existing_peer = Target(55, ("192.168.5.24", 1234))

        # Setup test context
        mods = MarketOperatorDataStore()
        mods.billing_server = existing_billing_server
        mods.participants[existing_peer.address] = existing_peer

        # Test input
        cyc = "some cycle context"
        msg = ContextMessage(cyc)

        # Execute test
        some_sender = Target(None, ("some address", "some port"))
        operator = BaseMarketOperatorMock(None)
        operator.handle_distribute_cycle_context(msg, some_sender)

        # Check cyc was sent to all participants
        for participant in mods.participants:
            (cyc, participant) in operator._sent
        (cyc, existing_billing_server) in operator._sent

        # Check response
        assert len(operator._replies) == 0
