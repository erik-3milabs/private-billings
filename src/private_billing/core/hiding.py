from __future__ import annotations
import math
import hashlib

from .serialize import Pickleable
from .utils import vector
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

    def __init__(self, cycle_length: int, mask_generator: SharedMaskGenerator) -> None:
        self.cycle_length = cycle_length
        self.cc = self._generate_crypto_context()
        self._key_pair = self._generate_key_pair()
        self.mask_generator = mask_generator

    @property
    def public_key(self):
        return self._key_pair.publicKey

    @property
    def _secret_key(self):
        return self._key_pair.secretKey

    @property
    def is_ready(self):
        """Whether this context is ready to hide/unhide data."""
        return self.mask_generator.is_stable

    def get_public_hiding_context(self) -> PublicHidingContext:
        return PublicHidingContext(self.cycle_length, self.cc, self.public_key)

    def get_masking_iv(self, round: int, obj_name: str) -> int:
        """
        Get an initialisation vector (iv) for masking.

        :param round: round of masking
        :param obj_name: name of object being masked
        :return: initialization vector
        """
        hash = hashlib.sha256(f"{round=}, {obj_name}".encode())
        return int.from_bytes(hash.digest(), "little")

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
        values.pad_to(self.cycle_length)  # pad to proper length
        ptxt = self.cc.MakeCKKSPackedPlaintext(values)  # pack
        return self.cc.Encrypt(self.public_key, ptxt)  # encrypt

    def decrypt(self, values: Ciphertext) -> vector[float]:
        """Decrypt a ciphertext to a list of values."""
        result = self.cc.Decrypt(values, self._secret_key)  # decrypt
        result.SetLength(self.cycle_length)  # unpack
        return vector(result.GetRealPackedValue())

    def invert_flags(self, flags: Ciphertext) -> Ciphertext:
        """
        Invert encrypted flags (i.e. 0 to 1, 1 to 0)

        :param flags: flags to invert
        :return: flipped flags
        """
        ones = [1] * self.cycle_length
        ptxt_ones = self.cc.MakeCKKSPackedPlaintext(ones)  # pack
        return self.cc.EvalSub(ptxt_ones, flags)

    def scale(self, ctxt: Ciphertext, scalars: vector[float]) -> Ciphertext:
        """
        Scale ciphertext with plaintext scalars

        :param ctxt: ciphertext
        :param scalars: plaintext scalar
        :param cc: cryptocontext
        :return: multiplied value, encrypted
        """
        ptxt_msg = self.cc.MakeCKKSPackedPlaintext(scalars)  # pack
        return self.cc.EvalMult(ctxt, ptxt_msg)  # multiply

    def multiply(self, ctxt_1: Ciphertext, ctxt_2: Ciphertext) -> Ciphertext:
        """Multiply ciphertexts"""
        return self.cc.EvalMult(ctxt_1, ctxt_2)

    def _generate_crypto_context(self) -> CryptoContext:
        """Generate the cryptographic context used in this context."""
        ciphertext_len = int(math.pow(2, math.ceil(math.log2(self.cycle_length))))
        dcrtBits = 55
        firstMod = 59

        parameters = CCParamsCKKSRNS()
        parameters.SetScalingModSize(dcrtBits)
        parameters.SetScalingTechnique(ScalingTechnique.FLEXIBLEAUTO)
        parameters.SetFirstModSize(firstMod)
        parameters.SetSecretKeyDist(SecretKeyDist.UNIFORM_TERNARY)

        parameters.SetRingDim(1 << 14)
        parameters.SetBatchSize(ciphertext_len)

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


class PublicHidingContext(HidingContext, Pickleable):
    def __init__(self, cycle_length: int, cc: CryptoContext, pk: PublicKey) -> None:
        self.cycle_length = cycle_length
        self.cc = cc
        self._public_key = pk

    @property
    def public_key(self):
        return self._public_key

    @property
    def _secret_key(self):
        raise NotImplementedError("not implemented for public")

    @property
    def is_ready(self):
        raise NotImplementedError("not implemented for public")

    def decrypt(self, values: Ciphertext) -> list[float]:
        raise NotImplementedError("not implemented for public")

    def _generate_crypto_context(self, cycle_length: int) -> CryptoContext:
        raise NotImplementedError("not implemented for public")

    def _generate_key_pair(self) -> KeyPair:
        raise NotImplementedError("not implemented for public")

    # OpenFHE has a bug where deserializing a EvalMultKey, it _replaces_
    # the previously known EvalMultKey(s), instead of _being added to the set_.
    # The following two functions provide a temporary work-around.
    # 
    # Before using a (received) PublicHidingContext, make sure to run 
    # its `activate_keys` function.
    #
    # Track the issue here:
    # https://github.com/openfheorg/openfhe-python/issues/144

    def activate_keys(self) -> None:
        from .serialize import OpenFHEDeserializer, OpenFHESerializer
        import functools
        tag = self._public_key.GetKeyTag()
        serialization = OpenFHESerializer._serialize_fhe_cc_key(
            functools.partial(self.cc.SerializeEvalMultKey, id=tag)
        )
        if len(serialization) < 1000:
            # Key is not present. Try to activate it.
            OpenFHEDeserializer._deserialize_from_file(
                self._relinearization_key_bytes, self.cc.DeserializeEvalMultKey
            )

    def __setstate__(self, state):
        relinearization_key_bytes = state["__cc__cc"][1]
        super().__setstate__(state)
        self._relinearization_key_bytes = relinearization_key_bytes
