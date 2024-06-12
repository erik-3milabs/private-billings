from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict

from .core import Data, HiddenData, CycleID, HiddenBill, Bill, CycleContext
from .server import TCPAddress, Signature, Message, MessageType, TransferablePublicKey


class UserType(Enum):
    EDGE = "edge"
    CORE = "core"


class ValidationException(Exception):
    pass


class BillingMessageType(MessageType):
    CONNECT = "connect"
    SEED = "seed"
    DATA = "data"
    HIDDEN_DATA = "hidden_data"
    GET_BILL = "get_bill"
    BILL = "bill"
    HIDDEN_BILL = "hidden_bill"
    CYCLE_CONTEXT = "cycle_context"
    GET_CYCLE_CONTEXT = "get_cycle_context"


@dataclass
class SignedMessage:
    message: Message
    signature: Signature

    def verify(self, pk: TransferablePublicKey) -> bool:
        pk.verify_signature(self.message, self.signature)


@dataclass
class ConnectMessage(Message):
    pk: bytes
    role: UserType
    network_state: Dict[TCPAddress, bytes]
    billing_state: Dict[str, Any]

    @property
    def type(self) -> MessageType:
        return BillingMessageType.CONNECT


@dataclass
class ContextMessage(Message):
    context: CycleContext

    @property
    def type(self) -> BillingMessageType:
        return BillingMessageType.CYCLE_CONTEXT


@dataclass
class GetBillMessage(Message):
    cycle_id: CycleID

    @property
    def type(self) -> BillingMessageType:
        return BillingMessageType.GET_BILL


@dataclass
class DataMessage(Message):
    data: Data

    @property
    def type(self) -> BillingMessageType:
        return BillingMessageType.DATA


@dataclass
class HiddenDataMessage(Message):
    data: HiddenData

    @property
    def type(self) -> BillingMessageType:
        return BillingMessageType.HIDDEN_DATA


@dataclass
class SeedMessage(Message):
    seed: int

    @property
    def type(self) -> MessageType:
        return BillingMessageType.SEED


@dataclass
class BillMessage(Message):
    bill: Bill

    @property
    def type(self) -> BillingMessageType:
        return BillingMessageType.BILL


@dataclass
class HiddenBillMessage(Message):
    hidden_bill: HiddenBill

    @property
    def type(self) -> BillingMessageType:
        return BillingMessageType.HIDDEN_BILL
