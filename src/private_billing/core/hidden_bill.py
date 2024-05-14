from __future__ import annotations
from dataclasses import dataclass
import pickle
from typing import Any
from .cycle import CycleID
from .serialize import (
    DeserializationOption,
    Serializible,
    deserialize_ciphertext,
    deserialize_fhe,
    serialize_fhe_obj,
)
from .bill import Bill
from .hiding import HidingContext
from openfhe import Ciphertext


@dataclass
class HiddenBill(Serializible):
    cycle_id: CycleID
    hidden_bill: Ciphertext
    hidden_reward: Ciphertext

    def reveal(self, hc: HidingContext):
        # decrypt
        bill = hc.decrypt(self.hidden_bill)
        reward = hc.decrypt(self.hidden_reward)

        # remove noise
        bill = [round(b, 5) for b in bill]
        reward = [round(r, 5) for r in reward]

        return Bill(self.cycle_id, bill, reward)

    def serialize(self) -> bytes:
        hb = serialize_fhe_obj(self.hidden_bill)
        hr = serialize_fhe_obj(self.hidden_reward)
        return pickle.dumps({"cycle_id": self.cycle_id, "hb": hb, "hr": hr})

    @staticmethod
    def deserialize(serialization: bytes) -> HiddenBill:
        obj = pickle.loads(serialization)
        hb = deserialize_fhe(obj["hb"], DeserializationOption.CIPHERTEXT)
        hr = deserialize_fhe(obj["hr"], DeserializationOption.CIPHERTEXT)
        return HiddenBill(obj["cycle_id"], hb, hr)

    def __getstate__(self) -> dict[str, Any]:
        """Prepare object for pickling, i.e., serialization."""
        # Prepare object for serialization
        self.__hidden_bill = serialize_fhe_obj(self.hidden_bill)
        self.__hidden_reward = serialize_fhe_obj(self.hidden_reward)

        # Disable unpickleable objects
        attributes = self.__dict__.copy()
        del attributes["hidden_bill"]
        del attributes["hidden_reward"]
        return attributes

    def __setstate__(self, state):
        """Rebuild object after unpickling, i.e., deserialization."""
        self.__dict__ = state

        # Rebuild objects
        self.hidden_bill = deserialize_ciphertext(self.__hidden_bill)
        self.hidden_reward = deserialize_ciphertext(self.__hidden_reward)
        
        # Remove placeholders
        del self.__hidden_bill
        del self.__hidden_reward
