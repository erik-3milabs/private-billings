from src.private_billing.core import vector


class TestVector:

    def test_add(self):
        v1 = vector([1, 2, 3])
        v2 = vector([4, 5, 6])
        assert v1 + v2 == vector([5, 7, 9])

    def test_sub(self):
        v1 = vector([1, 2, 3])
        v2 = vector([4, 5, 6])
        assert v1 - v2 == vector([-3, -3, -3])

    def test_div(self):
        v1 = vector([1, 2, 3])
        v2 = vector([4, 5, 6])
        assert v1 / v2 == vector([1 / 4, 2 / 5, 3 / 6])

    def test_mul(self):
        v1 = vector([1, 2, 3])
        v2 = vector([4, 5, 6])
        assert v1 * v2 == vector([4, 10, 18])
