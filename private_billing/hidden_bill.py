from dataclasses import dataclass
from .bill import Bill
from .hiding import HidingContext
from openfhe import Ciphertext

@dataclass
class HiddenBill:
    hidden_bill: Ciphertext
    hidden_reward: Ciphertext

    def reveal(self, hc: HidingContext):
        # decrypt
        bill = hc.decrypt(self.hidden_bill)
        reward = hc.decrypt(self.hidden_reward)

        # remove noise
        # TODO

        return Bill(bill, reward)
