from __future__ import annotations
from dataclasses import dataclass
import pickle

from private_billing.serialize import (
    DeserializationOption,
    Serializible,
    deserialize_fhe,
    deserialize_ciphertext,
    serialize_fhe_obj,
)
from .bill import Bill
from .hiding import HidingContext
from openfhe import Ciphertext


@dataclass
class HiddenBill(Serializible):
    hidden_bill: Ciphertext
    hidden_reward: Ciphertext

    def reveal(self, hc: HidingContext):
        # decrypt
        bill = hc.decrypt(self.hidden_bill)
        reward = hc.decrypt(self.hidden_reward)

        # remove noise
        bill = [round(b, 5) for b in bill]
        reward = [round(r, 5) for r in reward]

        return Bill(bill, reward)

    def serialize(self) -> bytes:
        hb = serialize_fhe_obj(self.hidden_bill)
        hr = serialize_fhe_obj(self.hidden_reward)
        return pickle.dumps({"hb": hb, "hr": hr})

    @staticmethod
    def deserialize(serialization: bytes) -> HiddenBill:
        obj = pickle.loads(serialization)
        hb = deserialize_fhe(obj["hb"], DeserializationOption.CIPHERTEXT)
        hr = deserialize_fhe(obj["hr"], DeserializationOption.CIPHERTEXT)
        return HiddenBill(hb, hr)
