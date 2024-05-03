from __future__ import annotations
from typing import TypeVar

Flag = int


class vector(list):
    """
    List of fixed length.
    Overrides __add__, __sub__, __mul__ and __div__ operations.
    """

    def new(len, val=0):
        return vector([val] * len)

    def __add__(self, o) -> vector:
        if not isinstance(o, vector):
            return super().__add__(o)
        assert len(self) == len(o)
        return vector([a + b for a, b in zip(self, o)])

    def __iadd__(self, o) -> vector:
        return self + o

    def __mul__(self, o) -> vector:
        # element-wise vector multiplication
        if isinstance(o, vector):
            assert len(self) == len(o)
            return vector([a * b for a, b in zip(self, o)])
        # scalar multiplication
        elif isinstance(o, (float, int)):
            return vector([a * o for a in self])
        return super().__mul__(o)

    def __imul__(self, o) -> vector:
        return self * o

    def __truediv__(self, o) -> vector:
        # element-wise vector division
        if isinstance(o, vector):
            assert len(self) == len(o)
            return vector([a / b for a, b in zip(self, o)])
        # scalar division
        elif isinstance(o, (float, int)):
            return vector([a / o for a in self])
        return super().__truediv__(o)

    def __itruediv__(self, o) -> vector:
        return self / o

    def __sub__(self, o) -> vector:
        if not isinstance(o, vector):
            return super().__sub__(o)
        assert len(self) == len(o)
        return vector([a - b for a, b in zip(self, o)])

    def __isub__(self, o) -> vector:
        return self - o

    def __mod__(self, o) -> vector:
        # element-wise vector modulo
        if isinstance(o, vector):
            assert len(self) == len(o)
            return vector([a % b for a, b in zip(self, o)])
        # scalar modulo
        elif isinstance(o, (float, int)):
            return vector([a % o for a in self])
        return super().__mod__(o)

    def __imod__(self, o) -> vector:
        return self % o


T = TypeVar("T")


def vec_sum(vals: list[vector[T]]) -> vector[T]:
    base = vector.new(len(vals[0]))
    for v in vals:
        base += v
    return base


def max_vector(vals: vector[T], o: T) -> vector[T]:
    """For a vector, compute for each element the max between it and `o`."""
    return vector([max(v, o) for v in vals])


def mulp_lists(v1: list[T], v2: list[T]) -> list[T]:
    """
    Element-wise multiply two lists.
    Assumes `v1` and `v2` have the same length.
    """
    return [a * b for a, b in zip(v1, v2)]


def get_positive_flags(vals: vector[T]) -> vector[Flag]:
    """Generate a series of flags indicating all positive entries in `vals`."""
    return vector([int(val > 0) for val in vals])
