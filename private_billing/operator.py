from typing import Dict, List
import uuid
from private_billing.client import Communicator, Sender, Message, Target
from private_billing import CycleContext, CycleID, ClientID


class Operator:

    def __init__(self):
        self.cycle_contexts: Dict[CycleID, CycleContext] = {}
        self.communicator = Communicator(self._receive)

        self.market_peers: List[Target] = []
        self.billing_server: Target = None

    def distribute_cycle_context(self, cyc: CycleContext) -> None:
        msg = Message("cycle_context", {"cyle_context": cyc})
        for peer in self.market_peers:
            self.communicator.send(peer, msg)
        self.communicator.send(self.billing_server, msg)

    def _receive(self, msg: Message, sender: Sender) -> None:
        call_backs = {
            "hello": self._receive_hello,
        }
        call_back = call_backs.get(msg.type)
        call_back(msg, sender)

    def _receive_hello(self, msg: Message, sender: Sender) -> None:
        new_id = self._generate_new_uuid()
        new_target = Target(new_id, sender.ip)

        new_target_type = msg.content.get("type")
        if new_target_type == "client":
            self._welcome_client(new_target)

            # Record new subscriber
            self.market_peers.append(new_target)
        elif new_target_type == "billing_server":
            self._welcome_server(new_target)

            # Record billing server
            self.billing_server = new_target

    def _welcome_client(self, client: Target) -> None:
        # Send welcome message to client
        welcome = Message(
            "welcome",
            {
                "id": client.id,
                "billing_server": self.billing_server,
                "peers": self.market_peers,
            },
        )
        self.communicator.send(welcome, client)

        # Send subscribe message to other peers
        for peer in self.market_peers:
            new_subscriber = Message("new_subscriber", {"new_subscriber": client})
            self.communicator.send(new_subscriber, peer)

    def _welcome_server(self, server: Target) -> None:
        # Send welcome messsage to server
        welcome = Message(
            "welcome",
            {"id": server.id, "billing_server": server, "peers": self.market_peers},
        )
        self.communicator.send(welcome, server)

        # Send new_server message to the clients
        for peer in self.market_peers:
            new_subscriber = Message("new_server", {"new_server": server})
            self.communicator.send(new_subscriber, peer)

    def _generate_new_uuid(self) -> ClientID:
        return uuid.uuid4().int
