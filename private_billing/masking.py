from .cycle import ClientID

from abc import ABC
import math
from numpy.random import PCG64
import secrets


class Int64Convertor(ABC):

    def convert_from_int64(self, val: int):
        """Convert a 64-bit int, to a desired format."""
        raise NotImplementedError("do not instatiate the abstract base class")


class Int64ToFloatConvertor(Int64Convertor):
    """
    Converts an int to a float (with the desired format).

    Creates a float with a sufficiently large integer part and fractional part.

    :param integer_size: size of the integral part to be converted
    :param fractional_size: size of the fractional part to be converted
    """

    def __init__(self, integer_size: int, fractional_size: int) -> None:
        assert (integer_size + fractional_size) <= 64 * math.log10(2)
        self.integer_size = integer_size
        self.fractional_size = fractional_size

    @property
    def modulus(self):
        return 10 ** (self.integer_size + self.fractional_size)

    @property
    def divisor(self):
        return 10**self.fractional_size

    def convert_from_int64(self, val: int) -> float:
        """Convert an 64-bit int to a float"""
        # Crop to desired size
        cropped = val % self.modulus

        # 'Shift' to the desired format
        return cropped / self.divisor

# TODO: PRZS

class SharedMaskGenerator:
    """
    TODO
    """
    
    def __init__(self, convertor: Int64Convertor) -> None:
        self.convertor = convertor
        self.owned_seeds: dict[ClientID, int] = {}
        self.foreign_seeds: dict[ClientID, int] = {}

    def get_seed_for_peer(self, c: ClientID) -> int:
        seed = self._generate_random_seed()
        self.owned_seeds[c] = seed
        return seed

    def consume_foreign_seed(self, seed: int, c: ClientID) -> None:
        self.foreign_seeds[c] = seed

    def generate_mask(self, iv: int) -> int:
        assert self.owned_seeds or self.foreign_seeds
        mask = 0

        for s in self.owned_seeds.values():
            mask += PCG64(s + iv).random_raw()

        for s in self.foreign_seeds.values():
            mask -= PCG64(s + iv).random_raw()

        return self.convertor.convert_from_int64(mask)

    def generate_masks(self, iv: int, size: int) -> list[int]:
        """
        Generate a list of masks
        
        :param iv: initialization vector for the randomness.
        :param size: number of masks to be generated.
        :returns: list of generated masks
        """
        masks = [0] * size

        # Add values generated with owned seeds
        for s in self.owned_seeds.values():
            pcg = PCG64(s + iv)
            share = [pcg.random_raw() for _ in range(size)]
            masks = [a + b for a, b in zip(masks, share)]
        
        # Subtract values generated with foreign seeds
        for s in self.foreign_seeds.values():
            pcg = PCG64(s + iv)
            share = [pcg.random_raw() for _ in range(size)]
            masks = [a - b for a, b in zip(masks, share)]
            
        return [self.convertor.convert_from_int64(m) for m in masks]
    
    @staticmethod
    def _generate_random_seed() -> int:
        return secrets.randbits(128)
