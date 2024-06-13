from typing import Dict

from .network import PeerToPeerBillingBaseServer, NodeInfo, no_verification_required
from .server import TCPAddress
from .core import CycleID, CycleContext, SharedBilling, ClientID, HiddenBill
from .messages import (
    ContextMessage,
    HiddenBillMessage,
    HiddenDataMessage,
    BillingMessageType,
    BillingMessageType,
    UserType,
)
from .log import logger


class EdgeServer(PeerToPeerBillingBaseServer):

    def __init__(self, address, cycle_length) -> None:
        super().__init__(address)
        self.shared_biller = SharedBilling()
        self.billing_state["cycle_length"] = cycle_length

    @property
    def role(self) -> UserType:
        return UserType.EDGE

    @property
    def handlers(self):
        return {
            **super().handlers,
            BillingMessageType.HIDDEN_DATA: self.handle_hidden_data,
            BillingMessageType.CYCLE_CONTEXT: self.handle_context_data,
        }

    ### Connect Message

    def register_node(self, node: NodeInfo) -> None:
        super().register_node(node)

        # Add client for billing
        self.shared_biller.include_client(node.id)

    ### Handle incoming context data

    @no_verification_required
    def handle_context_data(self, msg: ContextMessage, origin: NodeInfo) -> None:
        """Handle incoming `CycleContext` data."""
        self.shared_biller.record_contexts(msg.context)
        self.try_run_billing(msg.context.cycle_id)

        # Forward to all known peers
        self.broadcast_context_data(msg.context)

    def broadcast_context_data(self, context: CycleContext) -> None:
        """Broadcast `CycleContext` to all network participants"""
        msg = ContextMessage(self.address, context)
        self.broadcast(msg, self.network_peers)

    ### Handle incoming data

    def handle_hidden_data(self, msg: HiddenDataMessage, origin: NodeInfo) -> None:
        """Handle incoming `HiddenData` data."""
        # Register data
        self.shared_biller.record_data(msg.data)

        # Attempt to start billing process
        self.try_run_billing(msg.data.cycle_id)

    ### Perform billing tasks

    def try_run_billing(self, cycle_id: CycleID) -> None:
        """Attempt to run the billing process for the given cycle"""
        if self.shared_biller.is_ready(cycle_id):
            try:
                logger.info(f"start billing {cycle_id=}...")
                bills = self.run_billing(cycle_id)
                self.send_hidden_bills(bills)
                logger.info(f"finished billing {cycle_id=}")
            except Exception as e:
                logger.error(f"billing {cycle_id=} failed: {str(e)}")
        else:
            logger.info(f"not ready for billing {cycle_id=}")

    def run_billing(self, cycle_id: CycleID) -> None:
        """Run the billing process for the given cycle"""
        return self.shared_biller.compute_bills(cycle_id)

    def send_hidden_bills(self, bills: Dict[ClientID, HiddenBill]) -> None:
        """Send `bills` to the proper recipients."""
        for member in self.network_cores:
            bill = bills[member.id]
            self.send_hidden_bill(bill, member)

    def send_hidden_bill(self, bill: HiddenBill, target: NodeInfo) -> None:
        """Send `bill` to `target`."""
        bill_msg = HiddenBillMessage(self.address, bill)
        self.send(bill_msg, target)


def launch_edge(server_address: TCPAddress, cycle_len: int = 672) -> None:
    """
    Launch peer server
    :param server_address: address to host this server
    :param edge: information of network edge to attach to.
    """
    server = EdgeServer(server_address, cycle_len)
    server.start()
