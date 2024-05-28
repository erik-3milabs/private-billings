from __future__ import annotations
from enum import Enum
from pathlib import Path
import pickle
from tempfile import TemporaryDirectory
from typing import Any, Tuple
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


class OpenFHESerializer:

    @classmethod
    def serialize(cls, obj) -> bytes:
        """Serialize an FHE object"""
        serializers = {
            Ciphertext: cls._serialize_to_file,
            PublicKey: cls._serialize_to_file,
            CryptoContext: cls._serialize_fhe_cc,
        }
        serialize = serializers[type(obj)]
        return serialize(obj)

    @classmethod
    def _serialize_to_file(cls, obj) -> bytes:
        """Serialize FHE object to bytes."""
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "obj"
            SerializeToFile(str(path), obj, BINARY)
            return path.read_bytes()

    @classmethod
    def _serialize_fhe_cc_key(cls, serialization_func):
        """Serialize FHE CryptoContext key to bytes."""
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "obj"
            serialization_func(str(path), BINARY)
            return path.read_bytes()

    @classmethod
    def _serialize_fhe_cc(cls, cc: CryptoContext) -> Tuple[bytes]:
        """Serialize FHE CryptoContext to (tuple of) bytes."""
        cc_bytes = cls._serialize_to_file(cc)
        relinerization_key_bytes = cls._serialize_fhe_cc_key(cc.SerializeEvalMultKey)
        rotation_key_bytes = cls._serialize_fhe_cc_key(cc.SerializeEvalAutomorphismKey)
        return (cc_bytes, relinerization_key_bytes, rotation_key_bytes)


class OpenFHEDeserializer:

    @classmethod
    def deserialize(cls, serialization: bytes | Tuple[bytes], type: DeserializationOption):
        match type:
            case DeserializationOption.CIPHERTEXT:
                obj, _ = cls._deserialize_from_file(serialization, DeserializeCiphertext)
            case DeserializationOption.PUBLIC_KEY:
                obj, _ = cls._deserialize_from_file(serialization, DeserializePublicKey)
            case DeserializationOption.CRYPTO_CONTEXT:
                obj, _ = cls._deserialize_cc(serialization)
        return obj

    @classmethod
    def _deserialize_from_file(cls, serialization: bytes, deserialization_func) -> Any:
        with TemporaryDirectory() as tmpdir:
            # Write to file
            path = Path(tmpdir) / "obj"
            path.write_bytes(serialization)

            # Deserialize
            return deserialization_func(str(path), BINARY)

    @classmethod
    def _deserialize_cc(cls, serialization: Tuple[bytes]) -> CryptoContext:
        cc_bytes, relin_key_bytes, rotate_key_bytes = serialization
        cc, res = cls._deserialize_from_file(cc_bytes, DeserializeCryptoContext)
        res &= cls._deserialize_from_file(relin_key_bytes, cc.DeserializeEvalMultKey)
        res &= cls._deserialize_from_file(rotate_key_bytes, cc.DeserializeEvalAutomorphismKey)
        return cc, res


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
            serialized_val = OpenFHESerializer.serialize(val)
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
            deserialized_val = OpenFHEDeserializer.deserialize(val, serialization_type)
            setattr(self, name, deserialized_val)

            # Remove serialized obj
            delattr(self, prefixed_name)

        return
