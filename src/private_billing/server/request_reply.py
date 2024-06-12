from abc import ABC
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Optional

import zmq
from .encoding import Encoder


class MessageType(Enum):
    pass


@dataclass
class TCPAddress:
    interface: str
    port: int

    def __str__(self) -> str:
        return f"tcp://{self.interface}:{self.port}"

    def __hash__(self) -> int:
        return hash((self.interface, self.port))


@dataclass
class Message:
    reply_address: TCPAddress

    @property
    def type(self) -> MessageType:
        raise NotImplementedError()


@dataclass
class RequestReplyServer(ABC):
    """
    Request-Reply Server

    :param encoder: Encoder used to encode/decode messages to/from bytes.
    """

    encoder: Encoder

    def __post_init__(self):
        self.context = zmq.Context()
        self.sock = self.context.socket(zmq.REP)
        self.send_sock = self.context.socket(zmq.REQ)
        self.keep_running = True

    def terminate(self) -> None:
        """Set server terminate flag."""
        self.keep_running = False

    def start(self, port: int = 5555, interval: int = 1000) -> None:
        """
        Run server.
        :param port: port on which to run
        :param interval: interval at which one checks for the shutdown signal
        """
        # Setup
        self.sock.RCVTIMEO = interval
        self.sock.bind(str(TCPAddress("*", port)))

        # Run server
        self.keep_running = True
        while self.keep_running:
            msg = self.recv()
            if msg:
                self._handle(msg)

    def send(self, msg: Message, target: TCPAddress) -> Any:
        """Send `msg` to `target`."""
        with self.send_sock.connect(str(target)):
            enc = self.encoder.encode(msg)
            self.send_sock.send(enc)
            return self.send_sock.recv()

    def broadcast(self, msg: Message, targets: Iterable[TCPAddress]) -> None:
        """
        Broadcast message

        :param msg: msg to broadcast
        :param targets: addresses to broadcast to.
        """
        for target in targets:
            self.send(msg, target)

    def reply(self, msg: Message) -> Any:
        """
        Reply on the current connection.
        :param msg: msg to reply.
        """
        enc = self.encoder.encode(msg)
        return self.sock.send(enc)

    def recv(self) -> Optional[Message]:
        """
        Attempt to receive a message.
        :returns: message, or None if no message was received before timeout.
        """
        try:
            enc: bytes = self.sock.recv()
            return self.encoder.decode(enc)
        except zmq.error.Again:
            return None

    def _handle(self, msg: Message) -> None:
        """Handle incoming `msg`"""
        raise NotImplementedError()
