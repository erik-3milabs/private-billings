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
    def __init__(self, response_address: Tuple[str, int]) -> None:
        """Cutting away communication components."""
        server_mock = Namespace(server_address=response_address)
        super().__init__(None, None, server_mock)

        # Store responses and sent messages
        mods = MarketOperatorDataStore()
        mods.responses = []
        mods.sent = []


    def handle(self) -> None:
        """Not handling anything in this test"""
        pass

    def send(self, message: Message, target: Target):
        self.data.sent.append((message, target))

    def reply(self, msg: Message) -> None:
        self.data.responses.append(msg)

def clean_datastore(func, *args, **kwargs):
    """
    Used to indicate this handler will not provide a response.
    Makes sure to close the socket on the other side.
    """

    def wrapper(self, *args, **kwargs):
        MarketOperatorDataStore().__init__()  # reset datastore before a test
        func(self, *args, **kwargs)

    return wrapper


class TestBilling:

    @clean_datastore
    def test_handle_hello_first_client(self):
        # Test input
        new_peer = Target(None, ("Sender address", 1000))
        peer_response_address = ("Sender address", 5555)
        hello = HelloMessage(UserType.CLIENT, peer_response_address)

        # Execute test
        BaseMarketOperatorMock(peer_response_address).handle_hello(hello, new_peer)

        # Check client was registered
        mods = MarketOperatorDataStore()
        assert mods.participants[peer_response_address] != None
        assert mods.participants[peer_response_address].id != None

        # Check response
        assert len(mods.responses) == 1
        response = mods.responses[0]
        assert isinstance(response, WelcomeMessage)
        assert response.id != None
        assert response.billing_server == None
        assert response.peers == []

        # Check no other messages are sent
        assert mods.sent == []

    @clean_datastore
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
        BaseMarketOperatorMock(peer_response_address).handle_hello(hello, new_peer)

        # Check response includes peer and server information
        assert len(mods.responses) == 1
        response = mods.responses[0]
        assert isinstance(response, WelcomeMessage)
        assert response.id != None
        assert response.billing_server == mods.billing_server
        assert response.peers == [existing_peer]

        # Check previously registered peers + server are notified
        assert len(mods.sent) == 2
        targets = set()
        for msg, target in mods.sent:
            assert msg.new_member.id == response.id
            assert msg.new_member.address == peer_response_address
            assert msg.member_type == UserType.CLIENT
            targets.add(target)
        
        # Check all are notified
        assert targets == {existing_billing_server, existing_peer}

    @clean_datastore
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
        BaseMarketOperatorMock(server_response_address).handle_hello(hello, new_server)

        # Check server was registered properly
        assert mods.billing_server.address == server_response_address
        assert mods.participants == {existing_peer.address: existing_peer}

        # Check response
        assert len(mods.responses) == 1
        response = mods.responses[0]
        assert isinstance(response, WelcomeMessage)
        assert response.id != None
        assert response.billing_server.address == server_response_address
        assert response.peers == [existing_peer]

        # Check previously registered peers are notified
        assert len(mods.sent) == 1
        msg, target = mods.sent[0]
        assert target == existing_peer
        assert msg.new_member.id == response.id
        assert msg.new_member.address == server_response_address
        assert msg.member_type == UserType.SERVER
    
    @clean_datastore
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
        BaseMarketOperatorMock(None).handle_distribute_cycle_context(msg, some_sender)

        # Check cyc was sent to all participants
        for participant in mods.participants:
            (cyc,participant) in mods.sent
        (cyc, existing_billing_server) in mods.sent

        # Check response
        assert len(mods.responses) == 0
