from openfhe import *
from .cycle import CycleContext
from .masking import SharedMaskGenerator
from openfhe import CCParamsCKKSRNS, Ciphertext, CryptoContext, GenCryptoContext, KeyPair, PKESchemeFeature


class HidingContext:
    """Context used to hide/encrypt data."""

    def __init__(self, cyc: CycleContext, mask_generator: SharedMaskGenerator) -> None:
        self.cyc = cyc
        self.cc = self._generate_crypto_context(cyc)
        self.key_pair = self._generate_key_pair()
        self.mask_generator = mask_generator

    def mask(self, values: list[float], iv: int) -> list[float]:
        """
        Mask a list of values.

        :param values: values to be masked.
        :param iv: initialization vector used in random mask sampling.
        :returns: masked values
        """
        masks = self.mask_generator.generate_masks(iv, len(values))
        masked = [a + b for a, b in zip(values, masks)]
        return masked

    def encrypt(self, values: list[float]) -> Ciphertext:
        """Encrypt a list of values"""
        public_key = self.key_pair.publicKey
        ptxt = self.cc.MakeCKKSPackedPlaintext(values)  # pack
        return self.cc.Encrypt(public_key, ptxt)  # encrypt

    def decrypt(self, values: Ciphertext) -> list[float]:
        """Decrypt a ciphertext to a list of values."""
        secret_key = self.key_pair.secretKey
        result = self.cc.Decrypt(values, secret_key)  # decrypt
        result.SetLength(self.cyc.cycle_length)  # unpack
        return result

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
