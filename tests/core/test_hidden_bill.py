from src.private_billing.core import HiddenBill, HidingContext, vector, Bill


class TestHiddenBill:

    def test_reveal(self):
        hc = HidingContext(1024, None)
        enc_bill = hc.encrypt(vector.new(1024, 5))
        enc_reward = hc.encrypt(vector.new(1024, 55))
        hb = HiddenBill(5, enc_bill, enc_reward)

        bill = hb.reveal(hc)
        assert isinstance(bill, Bill)
        assert isinstance(bill.bill, vector)
        assert isinstance(bill.reward, vector)
        assert len(bill.bill) == 1024
        assert len(bill.reward) == 1024

        for v in bill.bill:
            assert abs(v - 5) < pow(10, -6)

        for v in bill.reward:
            assert abs(v - 55) < pow(10, -6)
