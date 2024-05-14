from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from .core import ClientID, HiddenBill, HiddenData, SEED, CycleContext, CycleID, Data
from .server import Message, MessageType, Target, MarketConfig, ADDRESS


class ValidationException(Exception):
    pass


class BillingMessageType(MessageType):
    HELLO = 0
    WELCOME = 1
    NEW_MEMBER = 2
    CYCLE_CONTEXT = 3
    GET_CYCLE_CONTEXT = 4
    DATA = 5
    HIDDEN_DATA = 6
    SEED = 7
    BILL = 8
    GET_BILL = 9
    BOOT = 10


class UserType(Enum):
    CLIENT = 0
    SERVER = 1


@dataclass
class HelloMessage(Message):
    user_type: UserType
    response_address: ADDRESS

    @property
    def type(self) -> BillingMessageType:
        return BillingMessageType.HELLO

    def check_validity(self) -> None:
        try:
            assert isinstance(self.user_type, UserType)
        except AssertionError:
            raise ValidationException("Invalid hello message")


@dataclass
class WelcomeMessage(Message):
    id: ClientID
    billing_server: Optional[Target]
    peers: List[Target]
    cycle_length: int

    @property
    def type(self) -> BillingMessageType:
        return BillingMessageType.WELCOME

    def check_validity(self) -> None:
        try:
            assert isinstance(self.id, int)
            assert isinstance(self.billing_server, (None, Target))
            assert isinstance(self.cycle_length, int)
            assert isinstance(self.peers, list)
            for peer in self.peers:
                assert isinstance(peer, Target)
        except AssertionError:
            raise ValidationException("Invalid welcome message")


@dataclass
class NewMemberMessage(Message):
    new_member: Target
    member_type: UserType

    @property
    def type(self) -> BillingMessageType:
        return BillingMessageType.NEW_MEMBER

    def check_validity(self) -> None:
        try:
            assert isinstance(self.new_member, Target)
            assert isinstance(self.member_type, UserType)
        except AssertionError:
            raise ValidationException("Invalid new subscriber message")


@dataclass
class ContextMessage(Message):
    context: CycleContext

    @property
    def type(self) -> BillingMessageType:
        return BillingMessageType.CYCLE_CONTEXT

    def check_validity(self) -> None:
        try:
            assert isinstance(self.context, CycleContext)
        except AssertionError:
            raise ValidationException("Invalid context message.")


@dataclass
class GetBillMessage(Message):
    cycle_id: CycleID

    @property
    def type(self) -> BillingMessageType:
        return BillingMessageType.GET_BILL

    def check_validity(self) -> None:
        try:
            assert isinstance(self.cycle_id, CycleID)
        except AssertionError:
            raise ValidationException("Invalid get bill message.")

@dataclass
class GetContextMessage(Message):
    cycle_id: CycleID

    @property
    def type(self) -> BillingMessageType:
        return BillingMessageType.GET_CYCLE_CONTEXT

    def check_validity(self) -> None:
        try:
            assert isinstance(self.cycle_id, CycleID)
        except AssertionError:
            raise ValidationException("Invalid get context message.")


@dataclass
class DataMessage(Message):
    data: Data

    @property
    def type(self) -> BillingMessageType:
        return BillingMessageType.DATA

    def check_validity(self) -> None:
        try:
            assert self.data.check_validity()
        except AssertionError:
            raise ValidationException("Invalid data message")


@dataclass
class HiddenDataMessage(Message):
    data: HiddenData

    @property
    def type(self) -> BillingMessageType:
        return BillingMessageType.HIDDEN_DATA

    def check_validity(self) -> None:
        try:
            assert self.data.check_validity()
        except AssertionError:
            raise ValidationException("Invalid data message")


@dataclass
class SeedMessage(Message):
    owner: ClientID
    seed: SEED

    @property
    def type(self) -> BillingMessageType:
        return BillingMessageType.SEED

    def check_validity(self) -> None:
        try:
            assert isinstance(self.seed, SEED)
        except AssertionError:
            raise ValidationException("invalid seed message")


@dataclass
class BillMessage(Message):
    bill: HiddenBill

    @property
    def type(self) -> BillingMessageType:
        return BillingMessageType.BILL

    def check_validity(self) -> None:
        try:
            assert isinstance(self.bill, HiddenBill)
        except AssertionError:
            raise ValidationException("Invalid bill message")


@dataclass
class BootMessage(Message):
    market_config: MarketConfig

    @property
    def type(self) -> BillingMessageType:
        return BillingMessageType.BOOT

    def check_validity(self) -> None:
        try:
            assert isinstance(self.market_config, MarketConfig)
        except AssertionError:
            raise ValidationException("Invalid bill message")
