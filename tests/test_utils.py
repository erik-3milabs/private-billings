from private_billing import (
    CycleContext,
    HidingContext,
    SharedMaskGenerator,
    Int64Convertor,
)


class TestConverter(Int64Convertor):
    def convert_from_int64(self, val: int):
        return val


def get_test_converter():
    return TestConverter()


def get_test_cycle_context(id, length: int):
    return CycleContext(
        id,
        length,
        [0.21] * length,
        [0.05] * length,
        [0.11] * length,
    )


def get_test_mask_generator():
    conv = get_test_converter()
    return SharedMaskGenerator(conv)

class MockHidingContext(HidingContext):
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
        pass
    
    def mask(self, values: list[float], iv: int) -> list[float]:
        return [v + iv for v in values]
    
    def encrypt(self, values: list[float]):
        return [v + 1 for v in values]

    def decrypt(self, values: list[float]):
        return [v - 1 for v in values]

def get_mock_hiding_context():
    return MockHidingContext("cyc", "mg")
