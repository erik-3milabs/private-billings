from dataclasses import dataclass
from .serialize import Serializible
from .utils import vector, Flag

CycleID = int
ClientID = int


@dataclass
class CycleContext(Serializible):
    cycle_id: CycleID
    cycle_length: int
    retail_prices: vector[float]
    feed_in_tarifs: vector[float]
    trading_prices: vector[float]

    def __post_init__(self) -> None:
        self.check_validity()

    def check_validity(self) -> None:
        """
        Check this concext to be valid.

        :raises: AssertionError when object is invalid.
        """
        assert len(self.retail_prices) == self.cycle_length
        assert len(self.feed_in_tarifs) == self.cycle_length
        assert len(self.trading_prices) == self.cycle_length


@dataclass
class SharedCycleData:
    total_deviations: vector[float]
    total_p2p_consumers: vector[float]
    total_p2p_producers: vector[float]

    @property
    def positive_total_deviation_flags(self) -> vector[Flag]:
        """
        Vector of flags indicating timeslots with a positive total deviation.
        """
        deviation_flags = vector()
        for dev in self.total_deviations:
            deviation_flags.append(Flag(dev > 0))
        return deviation_flags

    @property
    def negative_total_deviation_flags(self) -> vector[Flag]:
        """
        Vector of flags indicating timeslots with a negative total deviation.
        """
        deviation_flags = vector()
        for dev in self.total_deviations:
            deviation_flags.append(Flag(dev < 0))
        return deviation_flags

    def check_validity(self, cyc: CycleContext) -> None:
        """
        Check validity of this data, w.r.t. a cycle context.

        :param cyc: cycle context to check for
        :raises: AssertionError when object is invalid.
        """
        assert len(self.total_deviations) == cyc.cycle_length
        assert len(self.total_p2p_consumers) == cyc.cycle_length
        assert len(self.total_p2p_producers) == cyc.cycle_length
