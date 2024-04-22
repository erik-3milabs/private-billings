from __future__ import annotations

from private_billing.utils import vector
from .cycle import CycleContext
from .masking import SharedMaskGenerator
from openfhe import (
    CCParamsCKKSRNS,
    Ciphertext,
    CryptoContext,
    GenCryptoContext,
    KeyPair,
    PKESchemeFeature,
    PublicKey,
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
        return PublicHidingContext(self.cc, self.public_key)

    def mask(self, values: vector[float], iv: int) -> vector[float]:
        """
        Mask a list of values.

        :param values: values to be masked.
        :param iv: initialization vector used in random mask sampling.
        :returns: masked values
        """
        masks = self.mask_generator.generate_masks(iv, len(values))
        masked = vector([a + b for a, b in zip(values, masks)])
        return masked

    def encrypt(self, values: vector[float]) -> Ciphertext:
        """Encrypt a list of values"""
        ptxt = self.cc.MakeCKKSPackedPlaintext(values)  # pack
        return self.cc.Encrypt(self.public_key, ptxt)  # encrypt

    def decrypt(self, values: Ciphertext) -> vector[float]:
        """Decrypt a ciphertext to a list of values."""
        result = self.cc.Decrypt(values, self.secret_key)  # decrypt
        result.SetLength(self.cyc.cycle_length)  # unpack
        return vector(result)

    def invert_flags(self, vals: Ciphertext) -> Ciphertext:
        """
        Invert list of flags, i.e., values in the set {0, 1}

        :param vals: flags to invert
        :return: inverted flag list
        """
        ones = [1] * self.cc.GetEncodingParams().GetBatchSize()
        ptxt_ones = self.cc.MakeCKKSPackedPlaintext(ones)  # pack
        return self.cc.EvalSub(ptxt_ones, vals)

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
        self.cc.EvalMult(ctxt_1, ctxt_2)

    def _generate_crypto_context(self, cyc: CycleContext) -> CryptoContext:
        """Generate the cryptographic context used in this context."""
        parameters = CCParamsCKKSRNS()
        parameters.SetMultiplicativeDepth(2)
        parameters.SetScalingModSize(50)
        parameters.SetBatchSize(cyc.cycle_length)

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


class PublicHidingContext(HidingContext):
    def __init__(self, cc: CryptoContext, pk: PublicKey) -> None:
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
