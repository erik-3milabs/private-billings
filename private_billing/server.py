from private_billing.core import SharedBilling, ClientID, CycleID
from private_billing.client import Communicator, Message, Target, Target
from private_billing.messages import (
    DataMessage,
    HelloMessage,
    MessageType,
    NewMemberMessage,
    UserType,
    WelcomeMessage,
)


class BillingServer:

    def __init__(self, market_operator: Target) -> None:
        self.sb = SharedBilling()
        self.market_operator = market_operator
        self.communicator = Communicator(self._receive)
        self.id: ClientID = None

        # Register with market operator
        self._register()

    def _receive(self, msg: Message, sender: Target) -> None:
        call_backs = {
            MessageType.WELCOME: self._receive_welcome,
            MessageType.NEW_MEMBER: self._new_member,
            MessageType.DATA: self._receive_data,
        }
        call_back = call_backs.get(msg.type)
        call_back(msg, sender)

    def _register(self) -> None:
        hello = HelloMessage(UserType.SERVER)
        self.communicator.send(hello, self.market_operator)

    def _receive_welcome(self, msg: WelcomeMessage, sender: Target) -> None:
        self.id = msg.id
        for peer in msg.peers:
            self.sb.include_client(peer.id)

    def _new_member(self, msg: NewMemberMessage, sender: Target) -> None:
        if msg.member_type != UserType.CLIENT:
            return
        self.sb.include_client(msg.new_member.id)

    def _receive_data(self, msg: DataMessage, sender: Target) -> None:
        # Register data
        self.sb.record_data(msg.data, sender.id)

        # Attempt to start billing process
        self.attempt_billing(msg.data.cycle_id)

    def attempt_billing(self, cycle_id: CycleID) -> None:
        """Attempt to run the billing process for the given cycle"""
        if self.sb.is_ready(cycle_id):
            self.sb.compute_bills(cycle_id)
