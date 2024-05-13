from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

from private_billing.server.message_handler import ADDRESS
from .core import ClientID, HiddenBill, HiddenData, SEED, CycleContext
from .server import Message, MessageType, Target, MarketConfig


class ValidationException(Exception):
    pass


class BillingMessageType(MessageType):
    HELLO = 0
    WELCOME = 1
    NEW_MEMBER = 2
    CYCLE_CONTEXT = 3
    DATA = 4
    SEED = 5
    BILL = 6
    BOOT = 7


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
class DataMessage(Message):
    data: HiddenData

    @property
    def type(self) -> BillingMessageType:
        return BillingMessageType.DATA

    def check_validity(self) -> None:
        try:
            assert self.data.check_validity()
        except AssertionError:
            raise ValidationException("Invalid data message")


@dataclass
class SeedMessage(Message):
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
