from __future__ import annotations
from enum import Enum
from pathlib import Path
import pickle
from tempfile import TemporaryDirectory
from openfhe import (
    SerializeToFile,
    BINARY,
    DeserializeCiphertext,
    DeserializePublicKey,
    DeserializeCryptoContext,
)


class DeserializationError(Exception):
    pass


class Serializible:

    def serialize(self) -> bytes:
        return pickle.dumps(self)

    @staticmethod
    def deserialize(serialization: bytes) -> Serializible:
        return pickle.loads(serialization)


def serialize_fhe_obj(obj) -> bytes:
    with TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "obj"
        SerializeToFile(str(path), obj, BINARY)
        return path.read_bytes()


class DeserializationOption(Enum):
    CIPHERTEXT = 1
    PUBLIC_KEY = 2
    CRYPTO_CONTEXT = 3

def deserialize_fhe(serialization: bytes, type: DeserializationOption):
    deserialization_functions = {
        DeserializationOption.CIPHERTEXT: DeserializeCiphertext,
        DeserializationOption.PUBLIC_KEY: DeserializePublicKey,
        DeserializationOption.CRYPTO_CONTEXT: DeserializeCryptoContext
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
        
        

def deserialize_ciphertext(serialization: bytes):
    with TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "obj"
        path.write_bytes(serialization)
        ct, success = DeserializeCiphertext(str(path), BINARY)
        if not success:
            raise DeserializationError("Failed to deserialize ciphertext")
        return ct


def deserialize_publickey(serialization: bytes):
    with TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "obj"
        path.write_bytes(serialization)
        pk, success = DeserializePublicKey(str(path), BINARY)
        if not success:
            raise DeserializationError("Failed to deserialize public key")
        return pk


def deserialize_cryptocontext(serialization: bytes):
    with TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "obj"
        path.write_bytes(serialization)
        cc, success = DeserializeCryptoContext(str(path), BINARY)
        if not success:
            raise DeserializationError("Failed to deserialize crypto context")
        return cc
