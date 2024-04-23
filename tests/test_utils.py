from private_billing import (
    CycleContext,
    HidingContext,
    SharedMaskGenerator,
    Int64Convertor,
    PublicHidingContext,
)
from private_billing.utils import vector


class TestVector:

    def test_add(self):
        v1 = vector([1, 2, 3])
        v2 = vector([4, 5, 6])
        assert v1 + v2 == vector([5, 7, 9])

    def test_sub(self):
        v1 = vector([1, 2, 3])
        v2 = vector([4, 5, 6])
        assert v1 - v2 == vector([-3,-3,-3])

    def test_div(self):
        v1 = vector([1, 2, 3])
        v2 = vector([4, 5, 6])
        assert v1 / v2 == vector([1/4, 2/5, 3/6])

    def test_mul(self):
        v1 = vector([1, 2, 3])
        v2 = vector([4, 5, 6])
        assert v1 * v2 == vector([4, 10, 18])


class TestConvertor(Int64Convertor):
    def convert_from_int64(self, val: int):
        return val


def get_test_convertor():
    return TestConvertor()


def get_test_cycle_context(id, length: int):
    return CycleContext(
        id,
        length,
        vector([0.21] * length),
        vector([0.05] * length),
        vector([0.11] * length),
    )


def get_test_mask_generator():
    conv = get_test_convertor()
    return SharedMaskGenerator(conv)


class MockedHidingContext(HidingContext):
    """
    Mock for Hiding Context

    encrypt = add one
    decrypt = subtract one
    mask = value + iv
    """

    def __init__(self, cyc: CycleContext, mask_generator: SharedMaskGenerator) -> None:
        self.cyc = cyc
        self.mask_generator = mask_generator
        self.cc = "cc"

    @property
    def public_key(self):
        return "pk"

    @property
    def _secret_key(self):
        return "sk"

    def mask(self, values: list[float], iv: int) -> list[float]:
        return [v + iv for v in values]

    def encrypt(self, values: list[float]):
        return [v + 1 for v in values]

    def decrypt(self, values: list[float]):
        return [v - 1 for v in values]

    def get_public_hiding_context(self):
        return MockedPublicHidingContext("cyc", "cc", "pk")


def get_mock_hiding_context():
    return MockedHidingContext("cyc", "mg")


class MockedPublicHidingContext(PublicHidingContext):

    def invert_flags(self, vals):
        return vector([1 - v for v in vals])

    def encrypt(self, scalars: list[float], pk):
        return vector(scalars)

    def mult_with_scalar(self, ctxt, scalars: list[float]):
        return vector([c * s for c, s in zip(ctxt, scalars)])

    def multiply_ciphertexts(self, ctxt_1, ctxt_2):
        return vector([c1 * c2 for c1, c2 in zip(ctxt_1, ctxt_2)])

    def __eq__(self, o):
        return self.cc == o.cc and self.public_key == o.public_key


def get_mock_public_hiding_context():
    return MockedPublicHidingContext("cc", "pk")
