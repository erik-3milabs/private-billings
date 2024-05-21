from __future__ import annotations
from dataclasses import dataclass

from .utils import vector
from .cycle import CycleID
from .serialize import Pickleable
from .bill import Bill
from .hiding import HidingContext
from openfhe import Ciphertext


@dataclass
class HiddenBill(Pickleable):
    cycle_id: CycleID
    hidden_bill: Ciphertext
    hidden_reward: Ciphertext

    def reveal(self, hc: HidingContext):
        # decrypt
        bill = hc.decrypt(self.hidden_bill)
        reward = hc.decrypt(self.hidden_reward)

        # remove noise
        bill = vector([round(b, 5) for b in bill])
        reward = vector([round(r, 5) for r in reward])
        
        # truncate to proper length
        bill.truncate(hc.cycle_length)
        reward.truncate(hc.cycle_length)

        return Bill(self.cycle_id, bill, reward)
