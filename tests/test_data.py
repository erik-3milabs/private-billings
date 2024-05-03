import pytest
from src.private_billing.core import Data, vector
from .test_utils import get_test_cycle_context, get_mock_hiding_context


class TestDataValidity:

    def test_check_validity_correct(self):
        cycle_length = 1024
        cyc = get_test_cycle_context(1, cycle_length)

        d = Data(
            client=0,
            cycle_id=1,
            consumptions=vector([0.01] * cycle_length),
            supplies=vector([0.0] * cycle_length),
            consumption_promise=vector([0] * cycle_length),
            supply_promise=vector([0] * cycle_length),
            accepted_flags=vector([1] * cycle_length),
        )

        d.check_validity(cyc)

    def test_check_validity_both_consumption_and_supply(self):
        cycle_length = 1024
        cyc = get_test_cycle_context(1, cycle_length)

        d = Data(
            client=0,
            cycle_id=1,
            consumptions=vector([0.01] * cycle_length),
            supplies=vector([0.1] * cycle_length),
            consumption_promise=vector([0] * cycle_length),
            supply_promise=vector([0] * cycle_length),
            accepted_flags=vector([1] * cycle_length),
        )

        with pytest.raises(AssertionError):
            d.check_validity(cyc)

    def test_check_validity_wrong_id(self):
        cycle_length = 1024
        cyc = get_test_cycle_context(1, cycle_length)

        d = Data(
            client=0,
            cycle_id=0,
            consumptions=vector([0.01] * cycle_length),
            supplies=vector([0.005] * cycle_length),
            consumption_promise=vector([0] * cycle_length),
            supply_promise=vector([0] * cycle_length),
            accepted_flags=vector([1] * cycle_length),
        )

        with pytest.raises(AssertionError):
            d.check_validity(cyc)

    def test_check_validity_wrong_length(self):
        cycle_length = 1024
        cyc = get_test_cycle_context(1, 512)

        d = Data(
            client=0,
            cycle_id=1,
            consumptions=vector([0.01] * cycle_length),
            supplies=vector([0.005] * cycle_length),
            consumption_promise=vector([0] * cycle_length),
            supply_promise=vector([0] * cycle_length),
            accepted_flags=vector([1] * cycle_length),
        )

        with pytest.raises(AssertionError):
            d.check_validity(cyc)


class TestDataGetDeviations:

    def test_get_deviations_consumer_dev(self):
        cycle_length = 1024
        d = Data(
            client=0,
            cycle_id=0,
            consumption_promise=vector([0.05] * cycle_length),
            consumptions=vector([0.01] * cycle_length),
            supply_promise=vector([0.0] * cycle_length),
            supplies=vector([0.0] * cycle_length),
            accepted_flags=vector([1] * cycle_length),
        )

        assert d.get_individual_deviations() == [0.04] * cycle_length

    def test_get_deviations_supply_dev(self):
        cycle_length = 1024
        d = Data(
            client=0,
            cycle_id=0,
            consumption_promise=vector([0.0] * cycle_length),
            consumptions=vector([0.0] * cycle_length),
            supply_promise=vector([0.1] * cycle_length),
            supplies=vector([0.05] * cycle_length),
            accepted_flags=vector([1] * cycle_length),
        )

        assert d.get_individual_deviations() == [-0.05] * cycle_length

    def test_get_deviations_not_accepted(self):
        cycle_length = 1024
        d = Data(
            client=0,
            cycle_id=0,
            consumption_promise=vector([0.05] * cycle_length),
            consumptions=vector([0.01] * cycle_length),
            supply_promise=vector([1.0] * cycle_length),
            supplies=vector([1.5] * cycle_length),
            accepted_flags=vector([0] * cycle_length),
        )

        # Deviations should be zero, because we were not accepted for trading
        assert d.get_individual_deviations() == [0.0] * cycle_length


class TestDataGetDeviationFlags:

    def test_get_positive_devation_flags_for_positive_consumption_deviation(self):
        cycle_length = 1024
        d = Data(
            client=0,
            cycle_id=0,
            consumption_promise=vector([1] * cycle_length),
            consumptions=vector([2] * cycle_length),
            supply_promise=vector([0.0] * cycle_length),
            supplies=vector([0.0] * cycle_length),
            accepted_flags=vector([1] * cycle_length),
        )

        assert d.get_positive_deviation_flags() == [1] * cycle_length

    def test_get_positive_devation_flags_for_negative_consumption_deviation(self):
        cycle_length = 1024
        d = Data(
            client=0,
            cycle_id=0,
            consumption_promise=vector([5] * cycle_length),
            consumptions=vector([1] * cycle_length),
            supply_promise=vector([0.0] * cycle_length),
            supplies=vector([0.0] * cycle_length),
            accepted_flags=vector([1] * cycle_length),
        )

        assert d.get_positive_deviation_flags() == [0] * cycle_length
    
    def test_get_positive_devation_flags_for_positive_consumption_deviation_but_not_accepted(self):
        cycle_length = 1024
        d = Data(
            client=0,
            cycle_id=0,
            consumption_promise=vector([1] * cycle_length),
            consumptions=vector([5] * cycle_length),
            supply_promise=vector([0.0] * cycle_length),
            supplies=vector([0.0] * cycle_length),
            accepted_flags=vector([0] * cycle_length),
        )

        assert d.get_positive_deviation_flags() == [0] * cycle_length

    def test_get_positive_devation_flags_for_positive_production_deviation(self):
        cycle_length = 1024
        d = Data(
            client=0,
            cycle_id=0,
            consumption_promise=vector([0.0] * cycle_length),
            consumptions=vector([0.0] * cycle_length),
            supply_promise=vector([1] * cycle_length),
            supplies=vector([2] * cycle_length),
            accepted_flags=vector([1] * cycle_length),
        )

        assert d.get_positive_deviation_flags() == [1] * cycle_length

    def test_get_positive_devation_flags_for_negative_production_deviation(self):
        cycle_length = 1024
        d = Data(
            client=0,
            cycle_id=0,
            consumption_promise=vector([0.0] * cycle_length),
            consumptions=vector([0.0] * cycle_length),
            supply_promise=vector([2] * cycle_length),
            supplies=vector([0.5] * cycle_length),
            accepted_flags=vector([1] * cycle_length),
        )

        assert d.get_positive_deviation_flags() == [0] * cycle_length
    
    def test_get_positive_devation_flags_for_positive_production_deviation_but_not_accepted(self):
        cycle_length = 1024
        d = Data(
            client=0,
            cycle_id=0,
            consumption_promise=vector([0.0] * cycle_length),
            consumptions=vector([0.0] * cycle_length),
            supply_promise=vector([0.5] * cycle_length),
            supplies=vector([1] * cycle_length),
            accepted_flags=vector([0] * cycle_length),
        )

        assert d.get_positive_deviation_flags() == [0] * cycle_length


class TestDataHide:

    def test_hide(self):
        mhc = get_mock_hiding_context()

        cycle_length = 1024
        d = Data(
            client=0,
            cycle_id=0,
            consumption_promise=vector([0.05] * cycle_length),
            consumptions=vector([0.10] * cycle_length),
            supply_promise=vector([0.0] * cycle_length),
            supplies=vector([0.0] * cycle_length),
            accepted_flags=vector([1] * cycle_length),
        )

        hd = d.hide(mhc)

        consumer_flags = [1] * cycle_length
        producer_flags = [0] * cycle_length

        positive_deviations = [1] * cycle_length

        assert hd.client == d.client
        assert hd.cycle_id == d.cycle_id
        assert hd.consumptions == [c + 1 for c in d.consumptions]
        assert hd.supplies == [s + 1 for s in d.supplies]
        assert hd.accepted_flags == [f + 1 for f in d.accepted_flags]
        assert hd.positive_deviation_flags == [f + 1 for f in positive_deviations]
        assert hd.masked_individual_deviations == [
            d + 0 for d in d.get_individual_deviations()
        ]
        assert hd.masked_p2p_consumer_flags == [f + 1 for f in consumer_flags]
        assert hd.masked_p2p_producer_flags == [f + 2 for f in producer_flags]
        assert hd.phc == mhc.get_public_hiding_context()
