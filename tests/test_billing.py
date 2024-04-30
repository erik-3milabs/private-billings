from src.private_billing.core import SharedBilling, HiddenData, vector
from tests.test_utils import MockedHidingContext, get_test_cycle_context


class TestSharedBillingComputeBills:

    def test_compute_bills_consumer_no_deviation(self):
        cycle_length = 1024
        cyc = get_test_cycle_context(1, cycle_length)

        mhc = MockedHidingContext("cc", "mg")

        consumptions = vector([0.05] * cycle_length)
        supplies = vector([0.00] * cycle_length)
        accepted_flags = vector([1] * cycle_length)
        positive_deviation_flags = vector([0] * cycle_length)
        individual_deviations = vector([0] * cycle_length)
        p2p_consumer_flags = vector([1] * cycle_length)
        p2p_producer_flags = vector([0] * cycle_length)
        hd = HiddenData(
            0,
            1,
            consumptions,
            supplies,
            accepted_flags,
            positive_deviation_flags,
            individual_deviations,
            p2p_consumer_flags,
            p2p_producer_flags,
            phc=mhc.get_public_hiding_context(),
        )

        # Record data
        sb = SharedBilling()
        sb.client_data = {1: {0: hd}}
        sb.clients.update([0, 1])
        sb.cycle_contexts = {1: cyc}

        # Compute bill
        bills = sb.compute_bills(1)

        # Check bill is correct
        bill = bills[0]
        assert bill.hidden_bill == consumptions * cyc.trading_prices
        # Note: not checking rewards, since this is a consumer (see consumer flags)

    def test_compute_bills_consumer_with_deviation(self):
        cycle_length = 1024
        cyc = get_test_cycle_context(1, cycle_length)
        mhc = MockedHidingContext("cc", "mg")

        consumptions = vector([1.1] * cycle_length)
        supplies = vector([0.0] * cycle_length)
        accepted_flags = vector([1] * cycle_length)
        positive_deviation_flags = vector([1] * cycle_length)
        individual_deviations = vector([-0.1] * cycle_length)
        p2p_consumer_flags = vector([1] * cycle_length)
        p2p_producer_flags = vector([0] * cycle_length)
        hd = HiddenData(
            0,
            1,
            consumptions,
            supplies,
            accepted_flags,
            positive_deviation_flags,
            individual_deviations,
            p2p_consumer_flags,
            p2p_producer_flags,
            phc=mhc.get_public_hiding_context(),
        )

        # Record data
        sb = SharedBilling()
        sb.client_data = {1: {0: hd}}
        sb.clients.update([0, 1])
        sb.cycle_contexts = {1: cyc}

        # Compute bill
        bills = sb.compute_bills(1)

        # Check bill is correct
        bill = bills[0]
        assert bill.hidden_bill == consumptions * cyc.trading_prices + (
            individual_deviations * (cyc.retail_prices - cyc.trading_prices)
        )
        # Note: not checking rewards, since this is a consumer (see consumer flags)

    def test_compute_bills_producer_no_deviation(self):
        cycle_length = 1024
        cyc = get_test_cycle_context(1, cycle_length)

        mhc = MockedHidingContext("cc", "mg")

        consumptions = vector([0.0] * cycle_length)
        supplies = vector([0.05] * cycle_length)
        accepted_flags = vector([1] * cycle_length)
        positive_deviation_flags = vector([0] * cycle_length)
        individual_deviations = vector([0.0] * cycle_length)
        p2p_consumer_flags = vector([0] * cycle_length)
        p2p_producer_flags = vector([1] * cycle_length)
        hd = HiddenData(
            0,
            1,
            consumptions,
            supplies,
            accepted_flags,
            positive_deviation_flags,
            individual_deviations,
            p2p_consumer_flags,
            p2p_producer_flags,
            phc=mhc.get_public_hiding_context(),
        )

        # Record data
        sb = SharedBilling()
        sb.client_data = {1: {0: hd}}
        sb.clients.update([0, 1])
        sb.cycle_contexts = {1: cyc}

        # Compute bill
        bills = sb.compute_bills(1)

        # Check reward is correct
        bill = bills[0]
        assert bill.hidden_reward == supplies * cyc.trading_prices
        # Note: not checking bills, since this is a producer

    def test_compute_bills_producer_with_deviation(self):
        cycle_length = 1024
        cyc = get_test_cycle_context(1, cycle_length)

        mhc = MockedHidingContext("cc", "mg")

        consumptions = vector([0.0] * cycle_length)
        supplies = vector([1.1] * cycle_length)
        accepted_flags = vector([1] * cycle_length)
        positive_deviation_flags = vector([1] * cycle_length)
        individual_deviations = vector([0.1] * cycle_length)
        p2p_consumer_flags = vector([0] * cycle_length)
        p2p_producer_flags = vector([1] * cycle_length)
        hd = HiddenData(
            0,
            1,
            consumptions,
            supplies,
            accepted_flags,
            positive_deviation_flags,
            individual_deviations,
            p2p_consumer_flags,
            p2p_producer_flags,
            phc=mhc.get_public_hiding_context(),
        )

        # Record data
        sb = SharedBilling()
        sb.client_data = {1: {0: hd}}
        sb.clients.update([0, 1])
        sb.cycle_contexts = {1: cyc}

        # Compute bill
        bills = sb.compute_bills(1)

        # Check reward is correct
        bill = bills[0]
        assert bill.hidden_reward == supplies * cyc.trading_prices + (
            individual_deviations * (cyc.feed_in_tarifs - cyc.trading_prices)
        )
        # Note: not checking bills, since this is a producer
