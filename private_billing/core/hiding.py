from __future__ import annotations
import pickle
from .serialize import (
    Serializible,
    deserialize_cryptocontext,
    deserialize_publickey,
    serialize_fhe_obj,
)
from .utils import vector
from .cycle import CycleContext
from .masking import SharedMaskGenerator
from openfhe import (
    CCParamsCKKSRNS,
    Ciphertext,
    CryptoContext,
    GenCryptoContext,
    KeyPair,
    KeySwitchTechnique,
    PKESchemeFeature,
    PublicKey,
    ScalingTechnique,
    SecretKeyDist,
)


class HidingContext:
    """Context used to hide/encrypt data."""

    def __init__(self, cyc: CycleContext, mask_generator: SharedMaskGenerator) -> None:
        self.cyc = cyc
        self.cc = self._generate_crypto_context(cyc)
        self._key_pair = self._generate_key_pair()
        self.mask_generator = mask_generator

    @property
    def public_key(self):
        return self._key_pair.publicKey

    @property
    def _secret_key(self):
        return self._key_pair.secretKey

    def get_public_hiding_context(self) -> PublicHidingContext:
        return PublicHidingContext(self.cyc, self.cc, self.public_key)

    def mask(self, values: vector[float], iv: int) -> vector[float]:
        """
        Mask a list of values.

        :param values: values to be masked.
        :param iv: initialization vector used in random mask sampling.
        :returns: masked values
        """
        masks = self.mask_generator.generate_masks(iv, len(values))
        return values + masks

    def encrypt(self, values: vector[float]) -> Ciphertext:
        """Encrypt a list of values"""
        ptxt = self.cc.MakeCKKSPackedPlaintext(values)  # pack
        return self.cc.Encrypt(self.public_key, ptxt)  # encrypt

    def decrypt(self, values: Ciphertext) -> vector[float]:
        """Decrypt a ciphertext to a list of values."""
        result = self.cc.Decrypt(values, self._secret_key)  # decrypt
        result.SetLength(self.cyc.cycle_length)  # unpack
        return vector(result.GetRealPackedValue())

    def flip_bits(self, bits: Ciphertext) -> Ciphertext:
        """
        Flip encrypted bits

        :param bits: bits to flip
        :return: flipped flags
        """
        ones = [1] * self.cyc.cycle_length
        ptxt_ones = self.cc.MakeCKKSPackedPlaintext(ones)  # pack
        return self.cc.EvalSub(ptxt_ones, bits)

    def mult_with_scalar(self, ctxt: Ciphertext, scalars: vector[float]) -> Ciphertext:
        """
        Multiply ciphertext with plaintext scalars

        :param ctxt: ciphertext
        :param scalars: plaintext scalar
        :param cc: cryptocontext
        :return: multiplied value, encrypted
        """
        ptxt_msg = self.cc.MakeCKKSPackedPlaintext(scalars)  # pack
        return self.cc.EvalMult(ctxt, ptxt_msg)  # multiply

    def multiply_ciphertexts(
        self, ctxt_1: Ciphertext, ctxt_2: Ciphertext
    ) -> Ciphertext:
        """Multiply ciphertexts"""
        return self.cc.EvalMult(ctxt_1, ctxt_2)

    def _generate_crypto_context(self, cyc: CycleContext) -> CryptoContext:
        """Generate the cryptographic context used in this context."""
        dcrtBits = 55
        firstMod = 59

        parameters = CCParamsCKKSRNS()
        parameters.SetScalingModSize(dcrtBits)
        parameters.SetScalingTechnique(ScalingTechnique.FLEXIBLEAUTO)
        parameters.SetFirstModSize(firstMod)
        parameters.SetSecretKeyDist(SecretKeyDist.UNIFORM_TERNARY)

        parameters.SetRingDim(1 << 14)
        parameters.SetBatchSize(cyc.cycle_length)

        parameters.SetNumLargeDigits(4)
        parameters.SetKeySwitchTechnique(KeySwitchTechnique.HYBRID)
        parameters.SetMultiplicativeDepth(3)

        cc = GenCryptoContext(parameters)

        # Enable the PKE scheme features used in this application
        cc.Enable(PKESchemeFeature.PKE)
        cc.Enable(PKESchemeFeature.KEYSWITCH)
        cc.Enable(PKESchemeFeature.LEVELEDSHE)
        cc.Enable(PKESchemeFeature.ADVANCEDSHE)
        cc.Enable(PKESchemeFeature.FHE)

        return cc

    def _generate_key_pair(self) -> KeyPair:
        """Generate a (random) keypair."""
        keys = self.cc.KeyGen()
        self.cc.EvalMultKeyGen(keys.secretKey)
        return keys


class PublicHidingContext(HidingContext, Serializible):
    def __init__(self, cyc: CycleContext, cc: CryptoContext, pk: PublicKey) -> None:
        self.cyc = cyc
        self.cc = cc
        self._public_key = pk

    @property
    def public_key(self):
        return self._public_key

    @property
    def _secret_key(self):
        raise NotImplementedError("not implemented for public")

    def decrypt(self, values: Ciphertext) -> list[float]:
        raise NotImplementedError("not implemented for public")

    def _generate_crypto_context(self, cyc: CycleContext) -> CryptoContext:
        raise NotImplementedError("not implemented for public")

    def _generate_key_pair(self) -> KeyPair:
        raise NotImplementedError("not implemented for public")

    def serialize(self) -> bytes:
        cc = serialize_fhe_obj(self.cc)
        pk = serialize_fhe_obj(self._public_key)
        return pickle.dumps({"cyc": self.cyc, "cc": cc, "pk": pk})

    @staticmethod
    def deserialize(serialization: bytes) -> PublicHidingContext:
        obj = pickle.loads(serialization)
        cc = deserialize_cryptocontext(obj["cc"])
        pk = deserialize_publickey(obj["pk"])
        return PublicHidingContext(obj["cyc"], cc, pk)
