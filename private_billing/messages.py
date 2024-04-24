from abc import ABC
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
from private_billing import ClientID, HiddenBill, HiddenData, SEED
from private_billing.client import Target
from private_billing.cycle import CycleContext


class ValidationException(Exception):
    pass


class MessageType(Enum):
    HELLO = 0
    WELCOME = 1
    NEW_MEMBER = 2
    CYCLE_CONTEXT = 3
    DATA = 4
    SEED = 5
    BILL = 6


class UserType(Enum):
    CLIENT = 0
    SERVER = 1


class Message(ABC):

    @property
    def type(self) -> MessageType:
        """Type of this message."""
        raise NotImplementedError("Not implemented for abstract class")

    def check_validity(self) -> None:
        """
        Check the validity of the content of this message.
        :raises: ValidationException when invalid.
        """
        raise NotImplementedError("Not implemented for abstract class")


@dataclass
class HelloMessage(Message):
    user_type: UserType

    @property
    def type(self) -> MessageType:
        return MessageType.HELLO

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

    @property
    def type(self) -> MessageType:
        return MessageType.WELCOME

    def check_validity(self) -> None:
        try:
            assert isinstance(self.id, int)
            assert isinstance(self.billing_server, (None, Target))
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
    def type(self) -> MessageType:
        return MessageType.NEW_MEMBER

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
    def type(self) -> MessageType:
        return MessageType.CYCLE_CONTEXT
    
    def check_validity(self) -> None:
        try:
            assert isinstance(self.context, CycleContext)
        except AssertionError:
            raise ValidationException("Invalid context message.")

@dataclass
class DataMessage(Message):
    data: HiddenData

    @property
    def type(self) -> MessageType:
        return MessageType.DATA

    def check_validity(self) -> None:
        try:
            assert self.data.check_validity()
        except AssertionError:
            raise ValidationException("Invalid data message")


@dataclass
class SeedMessage(Message):
    seed: SEED

    @property
    def type(self) -> MessageType:
        return MessageType.SEED

    def check_validity(self) -> None:
        try:
            assert isinstance(self.seed, SEED)
        except AssertionError:
            raise ValidationException("invalid seed message")


@dataclass
class BillMessage(Message):
    bill: HiddenBill

    @property
    def type(self) -> MessageType:
        return MessageType.BILL

    def check_validity(self) -> None:
        try:
            assert isinstance(self.bill, HiddenBill)
        except AssertionError:
            raise ValidationException("Invalid bill message")
