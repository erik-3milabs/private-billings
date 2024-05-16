from __future__ import annotations
from enum import Enum
from pathlib import Path
import pickle
from tempfile import TemporaryDirectory
from typing import Any
from openfhe import (
    Ciphertext,
    CryptoContext,
    PublicKey,
    SerializeToFile,
    BINARY,
    DeserializeCiphertext,
    DeserializePublicKey,
    DeserializeCryptoContext,
)


class DeserializationOption(Enum):
    CIPHERTEXT = 1
    PUBLIC_KEY = 2
    CRYPTO_CONTEXT = 3


class DeserializationError(Exception):
    pass


class Pickleable:

    TYPE_TO_PREFIX = {
        Ciphertext: "__ct__",
        PublicKey: "__pk__",
        CryptoContext: "__cc__",
    }

    PREFIX_TO_TYPE = {
        "__ct__": DeserializationOption.CIPHERTEXT,
        "__pk__": DeserializationOption.PUBLIC_KEY,
        "__cc__": DeserializationOption.CRYPTO_CONTEXT,
    }

    def serialize(self):
        return pickle.dumps(self)

    @staticmethod
    def deserialize(serialization: bytes) -> Pickleable:
        return pickle.loads(serialization)

    def __getstate__(self) -> dict[str, Any]:
        """Prepare object for pickling, i.e., serialization."""

        # Serialize OpenFHE components
        to_remove = []
        for name, val in self.__dict__.copy().items():
            if not isinstance(val, tuple(self.TYPE_TO_PREFIX)):
                continue

            # Store serialization
            prefixed_name = self.TYPE_TO_PREFIX[type(val)] + name
            serialized_val = serialize_fhe_obj(val)
            setattr(self, prefixed_name, serialized_val)

            # Remove original object
            to_remove.append(name)

        attributes = self.__dict__.copy()
        for name in to_remove:
            del attributes[name]
        return attributes

    def __setstate__(self, state):
        """Rebuild object after unpickling, i.e., deserialization."""
        self.__dict__ = state

        # Rebuild objects
        for prefixed_name, val in self.__dict__.copy().items():
            prefix, name = prefixed_name[:6], prefixed_name[6:]
            if prefix not in self.PREFIX_TO_TYPE:
                continue

            # Rebuild object
            serialization_type = self.PREFIX_TO_TYPE[prefix]
            deserialized_val = deserialize_fhe(val, serialization_type)
            setattr(self, name, deserialized_val)

            # Remove serialized obj
            delattr(self, prefixed_name)

        return


def serialize_fhe_obj(obj) -> bytes:
    with TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "obj"
        SerializeToFile(str(path), obj, BINARY)
        return path.read_bytes()


def deserialize_fhe(serialization: bytes, type: DeserializationOption):
    deserialization_functions = {
        DeserializationOption.CIPHERTEXT: DeserializeCiphertext,
        DeserializationOption.PUBLIC_KEY: DeserializePublicKey,
        DeserializationOption.CRYPTO_CONTEXT: DeserializeCryptoContext,
    }

    with TemporaryDirectory() as tmpdir:
        # Write to file
        path = Path(tmpdir) / "obj"
        path.write_bytes(serialization)

        # Deserialize
        func = deserialization_functions[type]
        obj, success = func(str(path), BINARY)

    if not success:
        raise DeserializationError(f"Failed to deserialize {type}.")

    return obj
