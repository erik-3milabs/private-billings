import pytest
from private_billing import Bill
from tests.test_utils import get_test_cycle_context

class TestBillCheckValidity():

    def test_check_validity(self):
        cycle_len = 1024
        cyc = get_test_cycle_context(0, cycle_len)
        b = Bill([1.0] * cycle_len, [0.0] * cycle_len)
        
        b.check_validity(cyc)
        
    def test_check_validity_wrong_length(self):
        cycle_len = 1024
        cyc = get_test_cycle_context(0, cycle_len)
        b = Bill([1.0] * 1023, [0.0] * cycle_len)
        
        with pytest.raises(AssertionError):
            b.check_validity(cyc)

class TestBillTotal():
    
    def test_bill_total(self):
        cycle_len = 1024
        b = Bill([1.0] * cycle_len, [1.5] * cycle_len)
        assert b.total == sum([-0.5] * cycle_len)
        
    def test_bill_total_two(self):
        cycle_len = 1024
        b = Bill([i for i in range(cycle_len)], [i for i in range(cycle_len)])
        assert b.total == sum([0.0] * cycle_len)