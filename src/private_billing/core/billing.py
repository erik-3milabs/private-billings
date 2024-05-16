from .hidden_bill import HiddenBill
from .cycle import CycleContext, CycleID, ClientID
from .data import HiddenData


class SharedBilling:
    """
    Component computing the peer-to-peer bills.
    """

    def __init__(self) -> None:
        self.client_data: dict[CycleID, dict[ClientID, HiddenData]] = {}
        self.cycle_contexts: dict[CycleID, CycleContext] = {}
        self.clients: set[ClientID] = set()

    def record_data(self, data: HiddenData) -> None:
        """
        Record data for a given client.

        :param data: data to record,
        :param c: client to record data for.
        """
        self.client_data.setdefault(data.cycle_id, {})
        self.client_data.get(data.cycle_id)[data.client] = data

    def record_contexts(self, cyc: CycleContext) -> None:
        """
        Record a cycle context information

        :param cyc: context to record
        """
        self.cycle_contexts[cyc.cycle_id] = cyc

    def include_client(self, c: ClientID) -> None:
        """
        Include a client in coming billing cycles

        :param c: client to include
        """
        self.clients.add(c)

    def exclude_clients(self, c: ClientID) -> None:
        """
        Exclude a client from future billing cycles

        :param c: client to exclude.
        """
        if c in self.clients:
            self.clients.remove(c)

    def compute_bills(self, cid: CycleID) -> dict[ClientID, HiddenBill]:
        """
        Compute bills for all clients, for a given cycle.

        :param cid: cycle to compute bills for
        :raises ValueError: when asked to perform billing for a round it is not
        ready for.
        :return: map of clients and their bills
        """
        if not self.is_ready(cid):
            raise ValueError(f"cannot run billing for cycle {cid}")

        # Gather data for the specified cycle
        cycle_data = self.client_data[cid]
        cyc = self.cycle_contexts[cid]

        # Gather data for clients eligibile to participate in this billing cycle
        included_cycle_data = [cycle_data[c] for c in self.clients]

        # Compute the shared cycle data
        scd = HiddenData.unmask_data(included_cycle_data)
        scd.check_validity(cyc)

        bills = {}
        for c, data in cycle_data.items():
            bills[c] = data.compute_hidden_bill(scd, cyc)

        return bills

    def is_ready(self, cid: CycleID) -> bool:
        """
        Whether it is possible to compute bills for a given cycle.

        :param cid: id of cycle for which to check.
        :returns: whether it is possible.
        """
        cycle_data = self.client_data.get(cid, {})
        at_least_one = len(self.clients) > 0
        all_data_present = all(map(lambda c: c in cycle_data, self.clients))
        context_present = cid in self.cycle_contexts
        return at_least_one and all_data_present and context_present
