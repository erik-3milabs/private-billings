from typing import Dict, List
import uuid
from private_billing.client import Communicator, Target, Message, Target
from private_billing import CycleContext, CycleID, ClientID
from private_billing.messages import ContextMessage, HelloMessage, NewMemberMessage, UserType, WelcomeMessage, MessageType

class Operator:

    def __init__(self):
        self.cycle_contexts: Dict[CycleID, CycleContext] = {}
        self.communicator = Communicator(self._receive)

        self.market_peers: List[Target] = []
        self.billing_server: Target = None

    def distribute_cycle_context(self, cyc: CycleContext) -> None:
        msg = ContextMessage(cyc)
        for peer in self.market_peers:
            self.communicator.send(peer, msg)
        self.communicator.send(self.billing_server, msg)

    def _receive(self, msg: Message, sender: Target) -> None:
        call_backs = {
            MessageType.HELLO: self._receive_hello,
        }
        call_back = call_backs.get(msg.type)
        call_back(msg, sender)

    def _receive_hello(self, msg: HelloMessage, sender: Target) -> None:
        new_id = self._generate_new_uuid()
        new_target = Target(new_id, sender.ip)

        match msg.user_type:
            case UserType.CLIENT:
                self._welcome_client(new_target)

                # Record new subscriber
                self.market_peers.append(new_target)
            case UserType.SERVER:
                self._welcome_server(new_target)

                # Record billing server
                self.billing_server = new_target

    def _welcome_client(self, client: Target) -> None:
        # Send welcome message to client
        welcome_msg = WelcomeMessage(client.id, self.billing_server, self.market_peers)
        self.communicator.send(welcome_msg, client)

        # Send subscribe message to other peers
        for peer in self.market_peers:
            new_subscriber_msg = NewMemberMessage(client, UserType.CLIENT)
            self.communicator.send(new_subscriber_msg, peer)

    def _welcome_server(self, server: Target) -> None:
        # Send welcome messsage to server
        welcome_msg = WelcomeMessage(server.id, server, self.market_peers)
        self.communicator.send(welcome_msg, server)

        # Send new_server message to the clients
        for peer in self.market_peers:
            new_server_msg = NewMemberMessage(server, UserType.SERVER)
            self.communicator.send(new_server_msg, peer)

    def _generate_new_uuid(self) -> ClientID:
        return uuid.uuid4().int
