import pickle
from typing import Any
from abc import ABC


class Encoder(ABC):

    @staticmethod
    def encode(msg: Any) -> bytes:
        raise NotImplementedError()

    @staticmethod
    def decode(encoding: bytes) -> Any:
        raise NotImplementedError()


class PickleEncoder(Encoder):

    def encode(msg: Any) -> bytes:
        return pickle.dumps(msg)

    def decode(encoding: bytes) -> Any:
        return pickle.loads(encoding)
