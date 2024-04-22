from dataclasses import dataclass

CycleID = int
ClientID = int


@dataclass
class CycleContext:
    cycle_id: CycleID
    cycle_length: int
    retail_prices: list[float]
    feed_in_tarifs: list[float]
    trading_prices: list[float]

    def __post_init__(self):
        self.check_validity()

    def check_validity(self):
        assert len(self.retail_prices) == self.cycle_length
        assert len(self.feed_in_tarifs) == self.cycle_length
        assert len(self.trading_prices) == self.cycle_length


@dataclass
class SharedCycleData:
    total_deviations: list[float]
    total_p2p_consumers: list[float]
    total_p2p_producers: list[float]

    @property
    def positive_total_deviation_flags(self) -> list[int]:
        deviation_flags = []
        for dev in self.total_deviations:
            deviation_flags.append(int(dev > 0))
        return deviation_flags

    @property
    def negative_total_deviation_flags(self) -> list[int]:
        deviation_flags = []
        for dev in self.total_deviations:
            deviation_flags.append(int(dev < 0))
        return deviation_flags
