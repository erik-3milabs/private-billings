from .hidden_bill import HiddenBill
from .cycle import CycleContext, CycleID, ClientID
from .data import HiddenData


class SharedBilling:

    def __init__(self) -> None:
        self.client_data: dict[CycleID, dict[ClientID, HiddenData]] = {}
        self.cycle_contexts: dict[CycleID, CycleContext] = {}
        self.clients: set = set()

    def record_data(self, data: HiddenData, c: ClientID) -> None:
        self.client_data.setdefault(data.cycle_id, {})
        self.client_data.get(data.cycle_id)[c] = data

    def record_contexts(self, cyc: CycleContext) -> None:
        self.cycle_contexts[cyc.cycle_id] = cyc

    def include_client(self, c: ClientID) -> None:
        self.clients.add(c)

    def exclude_clients(self, c: ClientID) -> None:
        if c in self.clients:
            self.clients.remove(c)

    def compute_bills(self, cid: CycleID) -> dict[ClientID, HiddenBill]:
        """Compute bills for all clients, for a given cycle."""
        # Gather data for the specified cycle
        cycle_data = self.client_data[cid]
        cyc = self.cycle_contexts[cid]

        # Compute the shared cycle data
        scd = HiddenData.unmask_data(list(cycle_data.values()))
        scd.check_validity(cyc)

        bills = {}
        for c, data in cycle_data.items():
            bills[c] = data.compute_hidden_bill(scd, cyc)

        return bills
