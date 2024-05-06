from __future__ import annotations
from .hidden_data import HiddenData
from .cycle import CycleContext, CycleID, ClientID
from .hiding import HidingContext
from .utils import Flag, get_positive_flags, vector
from dataclasses import dataclass


@dataclass
class Data:
    client: ClientID
    cycle_id: CycleID
    consumptions: vector[float]
    supplies: vector[float]
    consumption_promises: vector[float]
    supply_promises: vector[float]
    accepted_flags: vector[Flag]

    @property
    def supply_deviations(self) -> vector[float]:
        """Deviation from the promised supply."""
        return self.supplies - self.supply_promises

    @property
    def consumption_deviations(self) -> vector[float]:
        """Deviation from the promised consumption."""
        return self.consumptions - self.consumption_promises

    @property
    def individual_deviations(self) -> vector[float]:
        """
        Compute individual deviations.

        Deviation is computed as the supply deviation minus the consumption
        deviation.

        An individual is only considered to be 'deviating' when they were
        accepted for trading for that timeslot. When not accepted, the
        deviation is zero.
        """
        return (
            self.supply_deviations - self.consumption_deviations
        ) * self.accepted_flags

    @property
    def positive_consumption_deviation_flags(self) -> vector[Flag]:
        """
        Vector of flags indicating timeslots in which a positive consumption
        deviation occurred.

        Note: one is only considered to deviate in timeslots where one is
        accepted for trading.
        """
        return get_positive_flags(self.consumption_deviations) * self.accepted_flags

    @property
    def positive_supply_deviation_flags(self) -> vector[Flag]:
        """
        Vector of flags indicating timeslots in which a positive supply
        deviation occurred.

        Note: one is only considered to deviate in timeslots where one is
        accepted for trading.
        """
        return get_positive_flags(self.supply_deviations) * self.accepted_flags

    @property
    def positive_deviation_flags(self) -> vector[float]:
        """
        Vector of flags indicating timeslots in which a positive supply or
        consumption deviation occurred.

        Note: one is only considered to deviate in timeslots where one is
        accepted for trading.
        """
        return (
            self.positive_consumption_deviation_flags
            ^ self.positive_supply_deviation_flags
        )

    @property
    def p2p_consumer_flags(self) -> vector[Flag]:
        """
        Vector of flags indicating timeslots in which one acted as a
        peer-to-peer consumer.

        One is considered a peer-to-peer consumer when they
        1) promise to consume, and
        2) are accepted for trading.
        """
        return get_positive_flags(self.consumption_promises) * self.accepted_flags

    @property
    def p2p_producer_flags(self) -> vector[Flag]:
        """
        Vector of flags indicating timeslots in which one acted as a
        peer-to-peer producer.

        One is considered a peer-to-peer produce when they
        1) promise to produce, and
        2) are accepted for trading.
        """
        return get_positive_flags(self.supply_promises) * self.accepted_flags

    def hide(self, hc: HidingContext) -> HiddenData:
        """
        Hide the data in this object.
        This is achieved by either encrypting or masking it.

        :param hc: context used to hide this object with.
        """
        return HiddenData(
            self.client,
            self.cycle_id,
            hc.encrypt(self.consumptions),
            hc.encrypt(self.supplies),
            hc.encrypt(self.accepted_flags),
            hc.encrypt(self.positive_deviation_flags),
            hc.mask(self.individual_deviations, 0),
            hc.mask(self.p2p_consumer_flags, 1),
            hc.mask(self.p2p_producer_flags, 2),
            hc.get_public_hiding_context(),
        )

    def check_validity(self, cyc: CycleContext) -> None:
        """
        Check validity of this cycle data

        :param cyc: context to check against
        :raises: AssertionError when invalid
        """
        assert cyc.cycle_id == self.cycle_id

        # Check vector lengths are correct
        assert len(self.consumptions) == cyc.cycle_length
        assert len(self.supplies) == cyc.cycle_length
        assert len(self.consumption_promises) == cyc.cycle_length
        assert len(self.supply_promises) == cyc.cycle_length
        assert len(self.accepted_flags) == cyc.cycle_length

        # Check either production or consumption is zero;
        # cannot both be non-zero
        for p, c in zip(self.supplies, self.consumptions):
            assert p == 0 or c == 0
