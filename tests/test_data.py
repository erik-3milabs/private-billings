import pytest
from src.private_billing.core import Data, vector
from .tools import get_test_cycle_context, get_mock_hiding_context


class TestDataValidity:

    def test_check_validity_correct(self):
        cycle_length = 1024
        cyc = get_test_cycle_context(1, cycle_length)

        d = Data(
            client=0,
            cycle_id=1,
            consumptions=vector.new(cycle_length, 0.01),
            supplies=vector.new(cycle_length, 0.0),
            consumption_promises=vector.new(cycle_length, 0),
            supply_promises=vector.new(cycle_length, 0),
            accepted_flags=vector.new(cycle_length, 1),
        )

        d.check_validity(cyc)

    def test_check_validity_both_consumption_and_supply(self):
        cycle_length = 1024
        cyc = get_test_cycle_context(1, cycle_length)

        d = Data(
            client=0,
            cycle_id=1,
            consumptions=vector.new(cycle_length, 0.01),
            supplies=vector.new(cycle_length, 0.1),
            consumption_promises=vector.new(cycle_length, 0),
            supply_promises=vector.new(cycle_length, 0),
            accepted_flags=vector.new(cycle_length, 1),
        )

        with pytest.raises(AssertionError):
            d.check_validity(cyc)

    def test_check_validity_wrong_id(self):
        cycle_length = 1024
        cyc = get_test_cycle_context(1, cycle_length)

        d = Data(
            client=0,
            cycle_id=0,
            consumptions=vector.new(cycle_length, 0.01),
            supplies=vector.new(cycle_length, 0.005),
            consumption_promises=vector.new(cycle_length, 0),
            supply_promises=vector.new(cycle_length, 0),
            accepted_flags=vector.new(cycle_length, 1),
        )

        with pytest.raises(AssertionError):
            d.check_validity(cyc)

    def test_check_validity_wrong_length(self):
        cycle_length = 1024
        cyc = get_test_cycle_context(1, cycle_length)

        wrong_length = 512
        d = Data(
            client=0,
            cycle_id=1,
            consumptions=vector.new(wrong_length, 0.01),
            supplies=vector.new(wrong_length, 0.005),
            consumption_promises=vector.new(wrong_length, 0),
            supply_promises=vector.new(wrong_length, 0),
            accepted_flags=vector.new(wrong_length, 1),
        )

        with pytest.raises(AssertionError):
            d.check_validity(cyc)


class TestDataGetDeviations:

    def test_get_deviations_consumer_dev(self):
        cycle_length = 1024
        d = Data(
            client=0,
            cycle_id=0,
            consumption_promises=vector.new(cycle_length, 0.05),
            consumptions=vector.new(cycle_length, 0.01),
            supply_promises=vector.new(cycle_length, 0.0),
            supplies=vector.new(cycle_length, 0.0),
            accepted_flags=vector.new(cycle_length, 1),
        )

        assert d.individual_deviations == vector.new(cycle_length, 0.04)

    def test_get_deviations_supply_dev(self):
        cycle_length = 1024
        d = Data(
            client=0,
            cycle_id=0,
            consumption_promises=vector.new(cycle_length, 0.0),
            consumptions=vector.new(cycle_length, 0.0),
            supply_promises=vector.new(cycle_length, 0.1),
            supplies=vector.new(cycle_length, 0.05),
            accepted_flags=vector.new(cycle_length, 1),
        )

        assert d.individual_deviations == vector.new(cycle_length, -0.05)

    def test_get_deviations_not_accepted(self):
        cycle_length = 1024
        d = Data(
            client=0,
            cycle_id=0,
            consumption_promises=vector.new(cycle_length, 0.05),
            consumptions=vector.new(cycle_length, 0.01),
            supply_promises=vector.new(cycle_length, 1.0),
            supplies=vector.new(cycle_length, 1.5),
            accepted_flags=vector.new(cycle_length, 0),
        )

        # Deviations should be zero, because we were not accepted for trading
        assert d.individual_deviations == vector.new(cycle_length, 0.0)


class TestDataGetDeviationFlags:

    def test_get_positive_devation_flags_for_positive_consumption_deviation(self):
        cycle_length = 1024
        d = Data(
            client=0,
            cycle_id=0,
            consumption_promises=vector.new(cycle_length, 1),
            consumptions=vector.new(cycle_length, 2),
            supply_promises=vector.new(cycle_length, 0.0),
            supplies=vector.new(cycle_length, 0.0),
            accepted_flags=vector.new(cycle_length, 1),
        )

        assert d.positive_deviation_flags == vector.new(cycle_length, 1)

    def test_get_positive_devation_flags_for_negative_consumption_deviation(self):
        cycle_length = 1024
        d = Data(
            client=0,
            cycle_id=0,
            consumption_promises=vector.new(cycle_length, 5),
            consumptions=vector.new(cycle_length, 1),
            supply_promises=vector.new(cycle_length, 0.0),
            supplies=vector.new(cycle_length, 0.0),
            accepted_flags=vector.new(cycle_length, 1),
        )

        assert d.positive_deviation_flags == vector.new(cycle_length, 0)

    def test_get_positive_devation_flags_for_positive_consumption_deviation_but_not_accepted(
        self,
    ):
        cycle_length = 1024
        d = Data(
            client=0,
            cycle_id=0,
            consumption_promises=vector.new(cycle_length, 1),
            consumptions=vector.new(cycle_length, 5),
            supply_promises=vector.new(cycle_length, 0.0),
            supplies=vector.new(cycle_length, 0.0),
            accepted_flags=vector.new(cycle_length, 0),
        )

        assert d.positive_deviation_flags == vector.new(cycle_length, 0)

    def test_get_positive_devation_flags_for_positive_production_deviation(self):
        cycle_length = 1024
        d = Data(
            client=0,
            cycle_id=0,
            consumption_promises=vector.new(cycle_length, 0.0),
            consumptions=vector.new(cycle_length, 0.0),
            supply_promises=vector.new(cycle_length, 1),
            supplies=vector.new(cycle_length, 2),
            accepted_flags=vector.new(cycle_length, 1),
        )

        assert d.positive_deviation_flags == vector.new(cycle_length, 1)

    def test_get_positive_devation_flags_for_negative_production_deviation(self):
        cycle_length = 1024
        d = Data(
            client=0,
            cycle_id=0,
            consumption_promises=vector.new(cycle_length, 0.0),
            consumptions=vector.new(cycle_length, 0.0),
            supply_promises=vector.new(cycle_length, 2),
            supplies=vector.new(cycle_length, 0.5),
            accepted_flags=vector.new(cycle_length, 1),
        )

        assert d.positive_deviation_flags == vector.new(cycle_length, 0)

    def test_get_positive_devation_flags_for_positive_production_deviation_but_not_accepted(
        self,
    ):
        cycle_length = 1024
        d = Data(
            client=0,
            cycle_id=0,
            consumption_promises=vector.new(cycle_length, 0.0),
            consumptions=vector.new(cycle_length, 0.0),
            supply_promises=vector.new(cycle_length, 0.5),
            supplies=vector.new(cycle_length, 1),
            accepted_flags=vector.new(cycle_length, 0),
        )

        assert d.positive_deviation_flags == vector.new(cycle_length, 0)


class TestDataHide:

    def test_hide(self):
        cycle_length = 1024
        mhc = get_mock_hiding_context()

        d = Data(
            client=0,
            cycle_id=0,
            consumption_promises=vector.new(cycle_length, 0.05),
            consumptions=vector.new(cycle_length, 0.10),
            supply_promises=vector.new(cycle_length, 0.0),
            supplies=vector.new(cycle_length, 0.0),
            accepted_flags=vector.new(cycle_length, 1),
        )

        hd = d.hide(mhc)

        consumer_flags = vector.new(cycle_length, 1)
        producer_flags = vector.new(cycle_length, 0)

        positive_deviations = vector.new(cycle_length, 1)

        assert hd.client == d.client
        assert hd.cycle_id == d.cycle_id
        assert hd.consumptions == [c + 1 for c in d.consumptions]
        assert hd.supplies == [s + 1 for s in d.supplies]
        assert hd.accepted_flags == [f + 1 for f in d.accepted_flags]
        assert hd.positive_deviation_flags == [f + 1 for f in positive_deviations]
        assert hd.masked_individual_deviations == [
            d + 0 for d in d.individual_deviations
        ]
        assert hd.masked_p2p_consumer_flags == [f + 1 for f in consumer_flags]
        assert hd.masked_p2p_producer_flags == [f + 2 for f in producer_flags]
        assert hd.phc == mhc.get_public_hiding_context()
