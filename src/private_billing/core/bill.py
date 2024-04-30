from dataclasses import dataclass
from .utils import vector
from .cycle import CycleContext, CycleID

@dataclass
class Bill:
    cycle_id: CycleID
    bill: vector[float]
    reward: vector[float]

    def check_validity(self, cyc: CycleContext) -> None:
        assert len(self.bill) == cyc.cycle_length
        assert len(self.reward) == cyc.cycle_length

    @property
    def total(self) -> float:
        return sum(self.bill) - sum(self.reward)
    