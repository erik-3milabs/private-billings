from src.private_billing.core import SharedBilling, HiddenData, vector
from .tools import MockedHidingContext, get_test_cycle_context


class TestSharedBillingComputeBills:

    def test_compute_bills_only_for_registered_participants(self):
        cycle_length = 1024
        cyc = get_test_cycle_context(1, cycle_length)

        mhc = MockedHidingContext("cc", "mg")
        hd = HiddenData(
            0,
            1,
            consumptions=vector.new(cycle_length, 0.05),
            supplies=vector.new(cycle_length, 0.00),
            accepted_flags=vector.new(cycle_length, 1),
            positive_deviation_flags=vector.new(cycle_length, 0),
            masked_individual_deviations=vector.new(cycle_length, 0),
            masked_p2p_consumer_flags=vector.new(cycle_length, 1),
            masked_p2p_producer_flags=vector.new(cycle_length, 0),
            phc=mhc.get_public_hiding_context(),
        )

        # Record data
        sb = SharedBilling()
        sb.record_contexts(cyc)
        sb.record_data(hd)

        # Do not include client
        # sb.include_client(hd.client) 
        
        # Should not be ready to compute bill, since no data is available
        assert not sb.is_ready(hd.cycle_id)

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
        sb.record_contexts(cyc)
        sb.record_data(hd)
        sb.include_client(hd.client)

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
        sb.record_contexts(cyc)
        sb.record_data(hd)
        sb.include_client(hd.client)

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
        sb.record_contexts(cyc)
        sb.record_data(hd)
        sb.include_client(hd.client)

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
        sb.record_contexts(cyc)
        sb.record_data(hd)
        sb.include_client(hd.client)

        # Compute bill
        bills = sb.compute_bills(1)

        # Check reward is correct
        bill = bills[0]
        assert bill.hidden_reward == supplies * cyc.trading_prices + (
            individual_deviations * (cyc.feed_in_tarifs - cyc.trading_prices)
        )
        # Note: not checking bills, since this is a producer
