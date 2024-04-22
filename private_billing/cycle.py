from dataclasses import dataclass
from .utils import vector

CycleID = int
ClientID = int


@dataclass
class CycleContext:
    cycle_id: CycleID
    cycle_length: int
    retail_prices: vector[float]
    feed_in_tarifs: vector[float]
    trading_prices: vector[float]

    def __post_init__(self):
        self.check_validity()

    def check_validity(self):
        assert len(self.retail_prices) == self.cycle_length
        assert len(self.feed_in_tarifs) == self.cycle_length
        assert len(self.trading_prices) == self.cycle_length


@dataclass
class SharedCycleData:
    total_deviations: vector[float]
    total_p2p_consumers: vector[float]
    total_p2p_producers: vector[float]

    @property
    def positive_total_deviation_flags(self) -> vector[int]:
        deviation_flags = vector()
        for dev in self.total_deviations:
            deviation_flags.append(int(dev > 0))
        return deviation_flags

    @property
    def negative_total_deviation_flags(self) -> vector[int]:
        deviation_flags = vector()
        for dev in self.total_deviations:
            deviation_flags.append(int(dev < 0))
        return deviation_flags

    def check_validity(self, cyc: CycleContext):
        """Check validity w.r.t. a cycle context"""
        assert len(self.total_deviations) == cyc.cycle_length
        assert len(self.total_p2p_consumers) == cyc.cycle_length
        assert len(self.total_p2p_producers) == cyc.cycle_length