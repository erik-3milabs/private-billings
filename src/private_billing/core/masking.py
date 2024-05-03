from .utils import vec_sum, vector
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
    def modulus(self) -> int:
        return 10**self.integer_size
        # return pow(2, math.ceil(math.log2(10) * self.integer_size))

    @property
    def _divisor(self) -> int:
        return 10**self.fractional_size
        # return pow(2, math.ceil(math.log2(10) * self.fractional_size))

    def convert_from_int64(self, val: int) -> float:
        """Convert an 64-bit int to a float"""
        # 'Shift' to desired format
        shifted = val / self._divisor

        # Crop to desired size
        # Crop to desired size
        cropped = math.fmod(shifted, self.modulus)

        # 'Shift' to the desired format
        # x = cropped / self._divisor
        return cropped


SEED = int

# TODO: PRZS


class SharedMaskGenerator:
    """
    TODO
    """

    def __init__(self, convertor: Int64Convertor) -> None:
        self.convertor = convertor
        self.owned_seeds: dict[ClientID, SEED] = {}
        self.foreign_seeds: dict[ClientID, SEED] = {}
       
    @property
    def is_stable(self) -> bool:
        """
        Specifies whether this generator is stable.
        This is to mean whether the set of peers it has generated seeds for
        fully overlaps with the set of peers it has received seeds from.
        """
        return set(self.owned_seeds.keys()) == set(self.foreign_seeds.keys())

    def get_seed_for_peer(self, c: ClientID) -> SEED:
        seed = self._generate_random_seed()
        self.owned_seeds[c] = seed
        return seed

    def has_seed_for_peer(self, c: ClientID) -> bool:
        return c in self.owned_seeds

    def consume_foreign_seed(self, seed: SEED, c: ClientID) -> None:
        self.foreign_seeds[c] = seed

    def generate_mask(self, iv: int) -> float:
        assert self.owned_seeds or self.foreign_seeds
        mask = 0

        for s in self.owned_seeds.values():
            val = PCG64(s + iv).random_raw()
            val = self.convertor.convert_from_int64(val)
            mask += val

        for s in self.foreign_seeds.values():
            val = PCG64(s + iv).random_raw()
            val = self.convertor.convert_from_int64(val)
            mask -= val

        return mask

    def generate_masks(self, iv: int, size: int) -> vector[float]:
        """
        Generate a list of masks

        :param iv: initialization vector for the randomness.
        :param size: number of masks to be generated.
        :returns: list of generated masks
        """
        masks = vector.new(size)

        # Add values generated with owned seeds
        for s in self.owned_seeds.values():
            pcg = PCG64(s + iv)
            share = vector([pcg.random_raw() for _ in range(size)])
            masks += self._convert_vector(share)

        # Subtract values generated with foreign seeds
        for s in self.foreign_seeds.values():
            pcg = PCG64(s + iv)
            share = vector([pcg.random_raw() for _ in range(size)])
            masks -= self._convert_vector(share)

        return masks

    def unmask(self, vals: list[vector]) -> vector:
        return vec_sum(vals)

    def _convert_vector(self, vals: vector[int]) -> vector:
        return vector([self.convertor.convert_from_int64(v) for v in vals])

    @staticmethod
    def _generate_random_seed() -> int:
        return secrets.randbits(128)
