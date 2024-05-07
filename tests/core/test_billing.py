from src.private_billing.core import SharedBilling, HiddenData, vector
from .tools import MockedHidingContext, get_test_cycle_context


class TestSharedBillingComputeBills:

    def test_compute_bills_consumer_no_deviation(self):
        cycle_length = 1024
        cyc = get_test_cycle_context(1, cycle_length)

        mhc = MockedHidingContext("cc", "mg")

        hd = HiddenData(
            0,
            1,
            consumptions=vector.new(cycle_length, 0.05),
            supplies=vector.new(cycle_length, 0.00),
            accepted_consumer_flags=vector.new(cycle_length, 1),
            accepted_producer_flags=vector.new(cycle_length, 0),
            positive_deviation_flags=vector.new(cycle_length, 0),
            individual_deviations=vector.new(cycle_length, 0),
            p2p_consumer_flags=vector.new(cycle_length, 1),
            p2p_producer_flags=vector.new(cycle_length, 0),
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
        assert bill.hidden_bill == hd.consumptions * cyc.trading_prices
        # Note: not checking rewards, since this is a consumer (see consumer flags)

    def test_compute_bills_consumer_with_deviation(self):
        cycle_length = 1024
        cyc = get_test_cycle_context(1, cycle_length)
        mhc = MockedHidingContext("cc", "mg")

        hd = HiddenData(
            0,
            1,
            consumptions=vector.new(cycle_length, 1.1),
            supplies=vector.new(cycle_length, 0.0),
            accepted_consumer_flags=vector.new(cycle_length, 1),
            accepted_producer_flags=vector.new(cycle_length, 0),
            positive_deviation_flags=vector.new(cycle_length, 1),
            individual_deviations=vector.new(cycle_length, -0.1),
            p2p_consumer_flags=vector.new(cycle_length, 1),
            p2p_producer_flags=vector.new(cycle_length, 0),
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
        assert bill.hidden_bill == hd.consumptions * cyc.trading_prices + (
            hd.individual_deviations * (cyc.retail_prices - cyc.trading_prices)
        )
        # Note: not checking rewards, since this is a consumer (see consumer flags)

    def test_compute_bills_producer_no_deviation(self):
        cycle_length = 1024
        cyc = get_test_cycle_context(1, cycle_length)

        mhc = MockedHidingContext("cc", "mg")

        hd = HiddenData(
            0,
            1,
            consumptions=vector.new(cycle_length, 0.0),
            supplies=vector.new(cycle_length, 0.05),
            accepted_consumer_flags=vector.new(cycle_length, 0),
            accepted_producer_flags=vector.new(cycle_length, 1),
            positive_deviation_flags=vector.new(cycle_length, 0),
            individual_deviations=vector.new(cycle_length, 0.0),
            p2p_consumer_flags=vector.new(cycle_length, 0),
            p2p_producer_flags=vector.new(cycle_length, 1),
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
        assert bill.hidden_reward == hd.supplies * cyc.trading_prices
        # Note: not checking bills, since this is a producer

    def test_compute_bills_producer_with_deviation(self):
        cycle_length = 1024
        cyc = get_test_cycle_context(1, cycle_length)

        mhc = MockedHidingContext("cc", "mg")

        hd = HiddenData(
            0,
            1,
            consumptions=vector.new(cycle_length, 0.0),
            supplies=vector.new(cycle_length, 1.1),
            accepted_consumer_flags=vector.new(cycle_length, 0),
            accepted_producer_flags=vector.new(cycle_length, 1),
            positive_deviation_flags=vector.new(cycle_length, 1),
            individual_deviations=vector.new(cycle_length, 0.1),
            p2p_consumer_flags=vector.new(cycle_length, 0),
            p2p_producer_flags=vector.new(cycle_length, 1),
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
        assert bill.hidden_reward == hd.supplies * cyc.trading_prices + (
            hd.individual_deviations * (cyc.feed_in_tarifs - cyc.trading_prices)
        )
        # Note: not checking bills, since this is a producer
