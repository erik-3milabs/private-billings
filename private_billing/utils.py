from typing import TypeVar

Flag = int

T = TypeVar("T")
    
def max_list(vals: list[T], o: T) -> list[T]:
    """For a list, compute for each element the max between it and `o`."""
    return [max(v, o) for v in vals]

def mulp_lists(v1: list[T], v2: list[T]) -> list[T]:
    """
    Element-wise multiply two lists.
    Assumes `v1` and `v2` have the same length.
    """
    return [a * b for a, b in zip(v1, v2)]

def get_positive_flags(vals: list[T]) -> list[Flag]:
    """Generate a series of flags indicating all positive entries in `vals`."""
    return [int(val > 0) for val in vals]

