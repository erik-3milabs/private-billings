import pytest
from src.private_billing.core import Bill, vector
from .tools import get_test_cycle_context


class TestBillCheckValidity:

    def test_check_validity(self):
        cycle_id, cycle_len = 0, 1024
        cyc = get_test_cycle_context(0, cycle_len)
        b = Bill(cycle_id, vector.new(cycle_len, 1.0), vector.new(cycle_len, 0.0))

        b.check_validity(cyc)

    def test_check_validity_wrong_length(self):
        cycle_id, cycle_len = 0, 1024
        cyc = get_test_cycle_context(0, cycle_len)
        b = Bill(cycle_id, vector.new(cycle_len - 1, 1.0), vector.new(cycle_len, 0.0))

        with pytest.raises(AssertionError):
            b.check_validity(cyc)


class TestBillTotal:

    def test_bill_total(self):
        cycle_id, cycle_len = 0, 1024
        b = Bill(cycle_id, [1.0] * cycle_len, [1.5] * cycle_len)
        assert b.total == -0.5 * cycle_len

    def test_bill_total_two(self):
        cycle_id, cycle_len = 0, 1024
        b = Bill(cycle_id, [i for i in range(cycle_len)], [i for i in range(cycle_len)])
        assert b.total == 0
