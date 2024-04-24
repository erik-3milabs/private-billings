from private_billing import (
    CycleContext,
    HiddenBill,
    HiddenData,
    HidingContext,
    PublicHidingContext,
    vector,
)
from tests.test_utils import get_mock_public_hiding_context


class TestHiddenDataSerialization:

    def test_hidden_data_serialization(self):
        cyc_length = 1024
        hd = HiddenData(
            0,
            1,
            vector([1] * cyc_length),
            vector([2] * cyc_length),
            vector([3] * cyc_length),
            vector([4] * cyc_length),
            vector([6] * cyc_length),
            vector([7] * cyc_length),
            vector([0] * cyc_length),
            get_mock_public_hiding_context(),
        )

        serialization = hd.serialize()

        # ... send to elsewhere ...

        hd1 = HiddenData.deserialize(serialization)

        assert hd1.client == hd.client
        assert hd1.cycle_id == hd.cycle_id
        assert hd1.consumptions == hd.consumptions
        assert hd1.supplies == hd.supplies
        assert hd1.accepted_flags == hd.accepted_flags
        assert hd1.positive_deviation_flags == hd.positive_deviation_flags
        assert hd1.masked_individual_deviations == hd.masked_individual_deviations
        assert hd1.masked_p2p_consumer_flags == hd.masked_p2p_consumer_flags
        assert hd1.masked_p2p_producer_flags == hd.masked_p2p_producer_flags
        assert hd1.phc == hd.phc


class TestPublicHidingContextSerialization:

    def test_public_hiding_context_serialization(self):
        cycle_length = 1024
        cyc = CycleContext(
            0,
            cycle_length,
            vector([0.21] * cycle_length),
            vector([0.11] * cycle_length),
            vector([0.05] * cycle_length),
        )
        hc = HidingContext(cyc, None)

        phc = hc.get_public_hiding_context()

        serialization = phc.serialize()

        # ... send over ...

        phc2 = PublicHidingContext.deserialize(serialization)

        assert phc.cyc == phc2.cyc
        assert phc.cc == phc2.cc

        # Test public key works
        vals = vector(list(range(1024)))
        enc = phc2.encrypt(vals)
        dec = hc.decrypt(enc)

        # remove noise
        dec = [round(x) for x in dec]
        assert dec == vals


class TestHiddenBillSerialization:

    def test_hidden_bill_serialization(self):
        cycle_length = 1024
        cyc = CycleContext(
            0,
            cycle_length,
            vector([0.21] * cycle_length),
            vector([0.11] * cycle_length),
            vector([0.05] * cycle_length),
        )
        hc = HidingContext(cyc, None)

        b, r = vector(list(range(1024))), vector(list(range(1024, 2048)))
        hb, hr = hc.encrypt(b), hc.encrypt(r)
        bill = HiddenBill(hb, hr)

        serialization = bill.serialize()

        # ... send over ...

        bill2 = HiddenBill.deserialize(serialization)
        b2, r2 = hc.decrypt(bill2.hidden_bill), hc.decrypt(bill2.hidden_reward)
        # remove noise
        b2 = [round(x) for x in b2]
        r2 = [round(x) for x in r2]

        assert b2 == b
        assert r2 == r


class TestCycleContextSerialization:

    def test_cycle_context_serialization(self):
        cycle_length = 1024
        cyc = CycleContext(
            0,
            cycle_length,
            vector([0.21] * cycle_length),
            vector([0.11] * cycle_length),
            vector([0.05] * cycle_length),
        )

        serialization = cyc.serialize()

        # ... send over ...

        cyc2 = cyc.deserialize(serialization)

        assert cyc.cycle_id == cyc2.cycle_id
        assert cyc.cycle_length == cyc2.cycle_length
        assert cyc.retail_prices == cyc2.retail_prices
        assert cyc.feed_in_tarifs == cyc2.feed_in_tarifs
        assert cyc.trading_prices == cyc2.trading_prices
