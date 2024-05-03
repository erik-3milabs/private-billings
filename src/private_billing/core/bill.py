from dataclasses import dataclass
from .utils import vector
from .cycle import CycleContext, CycleID


@dataclass
class Bill:
    """
    Plaintext representation of a peer-to-peer trading bill.

    :param cycle_id: id of the cycle to which this bill belongs
    :param bill: amount to pay, for each timeslot in this billing cycle.
    :param reward: amount rewarded, for each timeslot in this billing cycle.
    """

    cycle_id: CycleID
    bill: vector[float]
    reward: vector[float]

    def check_validity(self, cyc: CycleContext) -> None:
        """
        Check whether this bill is valid, with regard to the given context.

        :raises: AssertionError when object is invalid.
        """
        assert len(self.bill) == cyc.cycle_length
        assert len(self.reward) == cyc.cycle_length

    @property
    def total(self) -> float:
        """
        Total amount to be paid in this cycle.
        A negative value implies the bill owner is owed some amount.
        """
        return sum(self.bill) - sum(self.reward)
