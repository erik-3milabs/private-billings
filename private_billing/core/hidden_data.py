from __future__ import annotations
from openfhe import Ciphertext
from .hiding import PublicHidingContext
from .serialize import Serializible
from .hidden_bill import HiddenBill
from .cycle import CycleContext, CycleID, SharedCycleData, ClientID
from .utils import max_vector, vector
from dataclasses import dataclass


@dataclass
class HiddenData(Serializible):
    """
    :param client: id of client owning this data
    :param cycle_id: id of cycle to which this data belongs
    :param consumptions: Encrypted consumption, per timeslot
    :param supplies: Encrypted supply, per timeslot
    :param accepted_flags: Flags indicating timeslots for which peer-to-peer trading was accepted.
    :param positive_deviation_flags: Flags indicating timeslots with negative deviation
    :param masked_individual_deviations: Deviation information, masked
    :param masked_p2p_consumer_flags: Flag indicating timeslots in which this user was a p2p consumer, masked.
    :param masked_p2p_producer_flags: Flag indicating timeslots in which this user was a p2p producer, masked.
    :param phc: context under which the information is encrypted/hidden
    """

    client: ClientID
    cycle_id: CycleID
    consumptions: Ciphertext
    supplies: Ciphertext
    accepted_flags: Ciphertext
    positive_deviation_flags: Ciphertext
    masked_individual_deviations: vector[float]
    masked_p2p_consumer_flags: vector[float]
    masked_p2p_producer_flags: vector[float]
    phc: PublicHidingContext

    def check_validity(self, cyc: CycleContext) -> bool:
        # Check all encrypted data is correct
        # TODO

        # Check all masked data is correct
        assert len(self.masked_individual_deviations) == cyc.cycle_length
        assert len(self.masked_p2p_consumer_flags) == cyc.cycle_length
        assert len(self.masked_p2p_producer_flags) == cyc.cycle_length

    @staticmethod
    def unmask_data(cycle_data: list[HiddenData]) -> SharedCycleData:
        vec_len = len(cycle_data[0].masked_individual_deviations)
        total_deviations = vector.new(vec_len)
        consumer_counts = vector.new(vec_len)
        producer_counts = vector.new(vec_len)

        for datum in cycle_data:
            total_deviations += datum.masked_individual_deviations
            consumer_counts += datum.masked_p2p_consumer_flags
            producer_counts += datum.masked_p2p_producer_flags

        return SharedCycleData(total_deviations, consumer_counts, producer_counts)

    def compute_hidden_bill(
        self, scd: SharedCycleData, cyc: CycleContext
    ) -> HiddenBill:
        """Compute hidden bill based on this user data."""

        # Bump zero-counts to prevent division-by-zero problems.
        # Note that this does not affect the bills or rewards:
        # if for a given timeslot either count is 0, the positive_deviation_flags and negative_deviation_flags at that
        # timeslot for all consumers/producers must be 0 too in this scenario, these total_ values do not contribute
        # to any bill/reward.
        total_p2p_consumers = max_vector(scd.total_p2p_consumers, 1.0)
        total_p2p_producers = max_vector(scd.total_p2p_producers, 1.0)

        # Create rejected a dual to the accepted mask
        rejected_flags = self.phc.invert_flags(self.accepted_flags)

        # CASE: Client not accepted for P2P trading
        #  -> pay retail price for the consumption
        #  -> get feed-in tarif for the production
        bill_no_p2p = self.phc.mult_with_scalar(self.consumptions, cyc.retail_prices)
        bill_no_p2p = self.phc.multiply_ciphertexts(bill_no_p2p, rejected_flags)
        reward_no_p2p = self.phc.mult_with_scalar(self.supplies, cyc.feed_in_tarifs)
        reward_no_p2p = self.phc.multiply_ciphertexts(reward_no_p2p, rejected_flags)

        # CASE: Client was accepted for P2P trading
        base_bill = self.phc.mult_with_scalar(self.consumptions, cyc.trading_prices)
        base_reward = self.phc.mult_with_scalar(self.supplies, cyc.trading_prices)

        # CASE: total deviation = 0
        # consumer get their base_bill
        # producer get their base_reward

        # CASE: total deviation < 0
        # L-> demand > supply
        # L-> producers gets base_reward

        # CASE: individual dev <= 0
        # L> this consumer did not contribute to the over consumption
        # L> consumer gets base_bill

        # CASE: individual dev > 0
        # consumer gets a billSupplement buy their portion of what was used too much against retail price.
        # bill = (consumption - TD / nr_p2p_consumers) * tradingPrice + TD / nr_p2p_consumers * retailPrice
        #      = consumption * tradingPrice + TD / nr_p2p_consumers * (retailPrice - tradingPrice)
        #      = baseBill + TD / nr_p2p_consumers * (retail_price - trading price)
        # hence,
        # supplement = TD / nr_p2p_consumers * (retail_price - trading price)

        # some testing
        bill_supplement = (
            (cyc.retail_prices - cyc.trading_prices) / total_p2p_consumers
        ) * scd.total_deviations
        bill_supplement_ct = self.phc.mult_with_scalar(
            self.positive_deviation_flags, bill_supplement
        )
        bill_supplement_ct = self.phc.mult_with_scalar(
            bill_supplement_ct, scd.negative_total_deviation_flags
        )

        # CASE: TD > 0
        # demand < supply

        # consumers <- baseBill

        # CASE: indiv dev <= 0
        # producers <- baseReward

        # CASE: indiv dev > 0
        # producers get a penalty they sell their portion of what was produced too much against feedin tarif
        # reward = (supply - TD / nr_p2p_producers) * tradingPrice + TD / nr_p2p_producers * feedInTarif
        #        = supply * tradingPrice + (TD / nr_p2p_producers * (feedInTarif - tradingPrice)
        #        = baseReward + (TD / nr_p2p_producers * (feedInTarif - tradingPrice)
        # hence,
        # penalty = (TD / nr_p2p_producers) * (feedInTarif - tradingPrice)
        #
        # Note that the penalty is negative, since feedInTarif is assumed to be < tradingPrice
        reward_penalty = (
            (cyc.feed_in_tarifs - cyc.trading_prices) / total_p2p_producers
        ) * scd.total_deviations
        reward_penalty_ct = self.phc.mult_with_scalar(
            self.positive_deviation_flags, reward_penalty
        )
        reward_penalty_ct = self.phc.mult_with_scalar(
            reward_penalty_ct, scd.positive_total_deviation_flags
        )

        # Aggregating the P2P cases
        bill_p2p = base_bill + bill_supplement_ct
        bill_p2p = self.phc.multiply_ciphertexts(bill_p2p, self.accepted_flags)

        reward_p2p = base_reward + reward_penalty_ct
        reward_p2p = self.phc.multiply_ciphertexts(reward_p2p, self.accepted_flags)

        # Aggregating P2P and no-P2P cases
        bill = bill_p2p + bill_no_p2p
        reward = reward_p2p + reward_no_p2p

        return HiddenBill(self.cycle_id, bill, reward)
