from __future__ import annotations
from .hidden_data import HiddenData
from .cycle import CycleContext, CycleID, ClientID
from .hiding import HidingContext
from .utils import Flag, get_positive_flags, vector
from dataclasses import dataclass


@dataclass
class Data:
    """
    Gathered utilization data.

    :param client: id of the client owning the data.
    :param cycle_id: id of the cycle during which this data was gathered.
    :param utilization_promise: promise to utilize a certain amount of energy.
    :param utilization: the actual energy utilization.

    Note:
    - a positive utilization (promise) indicates (a) consumption (promise),
    - a negative utilization (promise) indicates (a) supply (promise),
    - a zero utilization (promise) indicates no consumption/production (promise).
    """

    client: ClientID
    cycle_id: CycleID
    utilization_promises: vector[float]
    utilizations: vector[float]

    @property
    def consumption_promises(self) -> vector[float]:
        """
        Amount of energy promised to consume, per timeslot.

        One is considered to promise consumption when the `utilization_promise`
        is greater than zero.
        """
        return self.utilization_promises * get_positive_flags(self.utilization_promises)

    @property
    def supply_promises(self) -> vector[float]:
        """
        Amount of energy promised to supply, per timeslot.

        One is considered to promise supply when the `utilization_promise`
        is less than zero.
        """
        inverted = self.utilization_promises * -1
        return inverted * get_positive_flags(inverted)

    @property
    def consumptions(self) -> vector[float]:
        """
        Amount of energy consumed, per timeslot.

        One is considered to consume when the `utilization` is greater than
        zero.
        """
        return self.utilizations * get_positive_flags(self.utilizations)

    @property
    def supplies(self) -> vector[float]:
        """
        Amount of energy supplied, per timeslot.

        One is considered to supply when the `utilization` is smaller than
        zero.
        """
        inverted = self.utilizations * -1
        return inverted * get_positive_flags(inverted)

    @property
    def accepted_consumer_flags(self) -> vector[Flag]:
        """
        Flags indicating timeslots at which user was accepted for peer to peer
        trading as a consumer.

        A positive promise is assumed to correspond with being accepted for
        trading as a consumer.
        """
        return get_positive_flags(self.utilization_promises)

    @property
    def accepted_producer_flags(self) -> vector[Flag]:
        """
        Flags indicating timeslots at which user was accepted for peer-to-peer
        trading as a producer.

        A negative promise is assumed to correspond with being accepted for
        trading as a producer.
        """
        return get_positive_flags(self.utilization_promises * -1)

    @property
    def supply_deviations(self) -> vector[float]:
        """Deviation from the promised supply."""
        return (self.supplies - self.supply_promises) * self.accepted_producer_flags

    @property
    def consumption_deviations(self) -> vector[float]:
        """Deviation from the promised consumption."""
        return (
            self.consumptions - self.consumption_promises
        ) * self.accepted_consumer_flags

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
        return self.supply_deviations - self.consumption_deviations

    @property
    def positive_consumption_deviation_flags(self) -> vector[Flag]:
        """
        Vector of flags indicating timeslots in which a positive consumption
        deviation occurred.

        Note: one is only considered to deviate in timeslots where one is
        accepted for trading.
        """
        return get_positive_flags(self.consumption_deviations)

    @property
    def positive_supply_deviation_flags(self) -> vector[Flag]:
        """
        Vector of flags indicating timeslots in which a positive supply
        deviation occurred.

        Note: one is only considered to deviate in timeslots where one is
        accepted for trading.
        """
        return get_positive_flags(self.supply_deviations)

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
            | self.positive_supply_deviation_flags
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
        return get_positive_flags(self.consumption_promises)

    @property
    def p2p_producer_flags(self) -> vector[Flag]:
        """
        Vector of flags indicating timeslots in which one acted as a
        peer-to-peer producer.

        One is considered a peer-to-peer produce when they
        1) promise to produce, and
        2) are accepted for trading.
        """
        return get_positive_flags(self.supply_promises)

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
            hc.encrypt(self.accepted_consumer_flags),
            hc.encrypt(self.accepted_producer_flags),
            hc.encrypt(self.positive_deviation_flags),
            hc.mask(
                self.individual_deviations,
                hc.get_masking_iv(self.cycle_id, "individual_deviations"),
            ),
            hc.mask(
                self.p2p_consumer_flags,
                hc.get_masking_iv(self.cycle_id, "p2p_consumer_flags"),
            ),
            hc.mask(
                self.p2p_producer_flags,
                hc.get_masking_iv(self.cycle_id, "p2p_producer_flags"),
            ),
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
        assert len(self.utilization_promises) == cyc.cycle_length
        assert len(self.utilizations) == cyc.cycle_length
