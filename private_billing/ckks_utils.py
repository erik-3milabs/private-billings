from openfhe import Ciphertext, CryptoContext, PublicKey

def invert_flags(vals: Ciphertext, cc: CryptoContext) -> Ciphertext:
    """
    Invert list of flags, i.e., values in the set {0, 1}

    :param vals: flags to invert
    :return: inverted flag list
    """
    ones = [1] * cc.GetEncodingParams().GetBatchSize()
    ptxt_ones = cc.MakeCKKSPackedPlaintext(ones)  # pack
    return cc.EvalSub(ptxt_ones, vals)

def ckks_encrypt(scalars: list[float], cc: CryptoContext, ckks_pk: PublicKey) -> Ciphertext:
    """
    Packs and encrypts scalars

    :param scalars: scalar to encrypt
    :param cc: context to encrypt under
    :param ckks_pk: public key to encrypt under
    :return: encrypted scalars
    """
    ptxt_msg = cc.MakeCKKSPackedPlaintext(scalars)  # pack
    return cc.Encrypt(ckks_pk, ptxt_msg)  # encrypt

def mult_with_scalar(ctxt: Ciphertext, scalars: list[float], cc: CryptoContext) -> Ciphertext:
    """
    Multiply ciphertext with plaintext scalars

    :param ctxt: ciphertext
    :param scalars: plaintext scalar
    :param cc: cryptocontext
    :return: multiplied value, encrypted
    """
    ptxt_msg = cc.MakeCKKSPackedPlaintext(scalars)  # pack
    return cc.EvalMult(ctxt, ptxt_msg)  # multiply
