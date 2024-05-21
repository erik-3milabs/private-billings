from src.private_billing.core import (
    CycleContext,
    HiddenBill,
    HiddenData,
    HidingContext,
    PublicHidingContext,
    vector,
)
from .tools import are_equal_ciphertexts


class TestHiddenDataSerialization:
    def test_hidden_data_serialization(self):
        cyc_length = 1024
        hc = HidingContext(cyc_length, None)

        hd = HiddenData(
            0,
            1,
            hc.encrypt(vector.new(cyc_length, 1)),
            hc.encrypt(vector.new(cyc_length, 2)),
            hc.encrypt(vector.new(cyc_length, 3)),
            hc.encrypt(vector.new(cyc_length, 4)),
            hc.encrypt(vector.new(cyc_length, 5)),
            vector.new(cyc_length, 6),
            vector.new(cyc_length, 7),
            vector.new(cyc_length, 0),
            hc.get_public_hiding_context(),
        )

        serialization = hd.serialize()

        # ... send to elsewhere ...

        hd1: HiddenData = HiddenData.deserialize(serialization)

        assert hd1.client == hd.client
        assert hd1.cycle_id == hd.cycle_id
        assert are_equal_ciphertexts(hd1.consumptions, hd.consumptions, hc)
        assert are_equal_ciphertexts(hd1.supplies, hd.supplies, hc)
        assert are_equal_ciphertexts(
            hd1.accepted_consumer_flags, hd.accepted_consumer_flags, hc
        )
        assert are_equal_ciphertexts(
            hd1.accepted_producer_flags, hd.accepted_producer_flags, hc
        )
        assert are_equal_ciphertexts(
            hd1.positive_deviation_flags, hd.positive_deviation_flags, hc
        )
        assert hd1.masked_individual_deviations == hd.masked_individual_deviations
        assert hd1.masked_p2p_consumer_flags == hd.masked_p2p_consumer_flags
        assert hd1.masked_p2p_producer_flags == hd.masked_p2p_producer_flags

        # Test if phcs are the same
        assert hd1.phc.cc == hd.phc.cc
        assert hd1.phc.cycle_length == hd.phc.cycle_length

        # Test if public keys work the same
        phc: PublicHidingContext = hd1.phc
        pt = vector(range(1024))
        enc = phc.encrypt(pt)
        dec = hc.decrypt(enc)
        dec = [round(x) for x in dec]
        assert dec == pt


class TestPublicHidingContextSerialization:

    def test_public_hiding_context_serialization(self):
        cycle_length = 1024
        hc = HidingContext(cycle_length, None)

        phc = hc.get_public_hiding_context()

        serialization = phc.serialize()

        # ... send over ...

        phc2 = PublicHidingContext.deserialize(serialization)

        assert phc.cycle_length == phc2.cycle_length
        assert phc.cc == phc2.cc

        # Test public key works
        vals = vector(range(1024))
        enc = phc2.encrypt(vals)
        dec = hc.decrypt(enc)

        # remove noise
        dec = [round(x) for x in dec]
        assert dec == vals


class TestHiddenBillSerialization:

    def test_hidden_bill_serialization(self):
        cycle_id, cycle_length = 0, 1024
        hc = HidingContext(cycle_length, None)

        b, r = vector(range(1024)), vector(range(1024, 2048))
        hb, hr = hc.encrypt(b), hc.encrypt(r)
        bill = HiddenBill(cycle_id, hb, hr)

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
        cycle_id, cycle_length = 0, 1024
        cyc = CycleContext(
            cycle_id,
            cycle_length,
            vector.new(cycle_length, 0.21),
            vector.new(cycle_length, 0.11),
            vector.new(cycle_length, 0.05),
        )

        serialization = cyc.serialize()

        # ... send over ...

        cyc2: CycleContext = CycleContext.deserialize(serialization)

        assert cyc.cycle_id == cyc2.cycle_id
        assert cyc.cycle_length == cyc2.cycle_length
        assert cyc.retail_prices == cyc2.retail_prices
        assert cyc.feed_in_tarifs == cyc2.feed_in_tarifs
        assert cyc.trading_prices == cyc2.trading_prices
