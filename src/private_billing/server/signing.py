from dataclasses import dataclass
import pickle
from typing import Any
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from cryptography.hazmat.primitives.asymmetric import ec, utils


@dataclass
class Signature:
    signature: bytes
    hash_alg: hashes.HashAlgorithm


@dataclass
class TransferablePublicKey:
    public_key_bytes: bytes
    encoding: Encoding
    format: PublicFormat

    def __init__(
        self,
        public_key: ec.EllipticCurvePublicKey,
        encoding: Encoding = Encoding.PEM,
        format: PublicFormat = PublicFormat.SubjectPublicKeyInfo,
    ):
        self.public_key_bytes = public_key.public_bytes(encoding, format)
        self.encoding = encoding
        self.format = format

    @property
    def public_key(self):
        match self.encoding:
            case Encoding.PEM:
                return serialization.load_pem_public_key(self.public_key_bytes)
            case Encoding.OpenSSH:
                return serialization.load_ssh_public_key(self.public_key_bytes)
            case Encoding.DER:
                return serialization.load_der_public_key(self.public_key_bytes)
            case _:
                return NotImplementedError("")


class Signer:

    def __init__(self, curve=ec.SECP256K1) -> None:
        self.private_key = ec.generate_private_key(curve)

    @property
    def public_key(self) -> ec.EllipticCurvePublicKey:
        return self.private_key.public_key()

    def get_transferable_public_key(
        self,
        encoding: Encoding = Encoding.PEM,
        format: PublicFormat = PublicFormat.SubjectPublicKeyInfo,
    ) -> TransferablePublicKey:
        return TransferablePublicKey(self.public_key, encoding, format)

    def sign(
        self,
        obj: Any | bytes,
        hash_alg: hashes.HashAlgorithm = hashes.SHA256(),
    ) -> Signature:
        """
        Sign object under this Signer's private key

        :param obj: object to sign
        :param hash_alg: algorithm used to hash obj to usable size
        :return: signature for obj
        """
        if not isinstance(obj, bytes):
            obj = pickle.dumps(obj)
        digest = self._hash_obj(obj, hash_alg)
        signature = self.private_key.sign(digest, ec.ECDSA(utils.Prehashed(hash_alg)))
        return Signature(signature, hash_alg)

    @classmethod
    def verify(
        cls,
        obj: Any | bytes,
        sig: Signature,
        public_key: ec.EllipticCurvePublicKey | TransferablePublicKey,
    ) -> None:
        """
        Verify a signature on a given object.

        :param obj: object to verify signature for.
        :param sig: signature for object
        :param public_key: key used for signature verification
        :raises: InvalidSignature when signature is invalid for the object under the given key
        """
        if isinstance(public_key, TransferablePublicKey):
            public_key = public_key.public_key
        if not isinstance(obj, bytes):
            obj = pickle.dumps(obj)

        digest = cls._hash_obj(obj, sig.hash_alg)
        public_key.verify(
            sig.signature, digest, ec.ECDSA(utils.Prehashed(sig.hash_alg))
        )

    @staticmethod
    def _hash_obj(obj: bytes, hash_alg: hashes.HashAlgorithm) -> bytes:
        hasher = hashes.Hash(hash_alg)
        hasher.update(obj)
        return hasher.finalize()
