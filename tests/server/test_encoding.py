from src.private_billing.server.encoding import PickleEncoder


class TestPrickleEncoder:

    def test_encode_decode_consistent(self) -> None:
        some_obj = {"Hello": {0: 1, 2: 3}, "bye": set(("value", "value"))}
        enc = PickleEncoder.encode(some_obj)
        dec = PickleEncoder.decode(enc)
        assert dec == some_obj
