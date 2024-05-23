from abc import ABC
from dataclasses import dataclass
from enum import Enum
import pickle
import socket
from socketserver import BaseRequestHandler
from typing import Callable, Dict, Optional, Tuple
from uuid import UUID

import logging

logger = logging.getLogger(__name__)


class MessageType(Enum):
    pass


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


IP = str
PORT = int
ADDRESS = Tuple[IP, PORT]


@dataclass
class Target:
    id: UUID
    address: ADDRESS

    @property
    def ip(self):
        return self.address[0]

    @property
    def port(self):
        return self.address[1]

    def __hash__(self):
        return hash((self.id, self.address))


def no_response(func):
    """
    Used to indicate this handler will not provide a response.
    Makes sure to close the socket on the other side.
    """

    def wrapper(self, *args, **kwargs):
        self.reply("")
        func(self, *args, **kwargs)

    return wrapper


class MessageSender:

    @classmethod
    def encode(cls, message: Message) -> bytes:
        return pickle.dumps(message)

    @classmethod
    def decode(cls, enc_msg: bytes) -> Message:
        return pickle.loads(enc_msg)

    @classmethod
    def _send(cls, sock: socket.socket, message: Message) -> None:
        logger.info(f"[{sock.getsockname()}] sending {msg=} to {sock.getpeername()}")
        
        # Encode message
        enc_msg = cls.encode(message)

        # Send header
        msg_len = len(enc_msg)
        msg_len_bytes = msg_len.to_bytes(8, "little")
        logger.debug(f"[{sock.getsockname()}] -> sending header: {msg_len=}")
        sock.send(msg_len_bytes)

        # Send content
        if msg_len > 0:
            logger.debug(f"[{sock.getsockname()}] -> sending content.")
            sock.sendall(enc_msg)
            
        logger.debug(f"[{sock.getsockname()}] -> message sent.")

    @classmethod
    def _recvall(cls, sock: socket.socket, count):
        """Receive `count` bytes from `sock`."""
        buf = bytes()
        while count:
            newbuf = sock.recv(count)
            if not newbuf:
                return None
            buf += newbuf
            count -= len(newbuf)
        return buf

    @classmethod
    def _receive(cls, sock: socket.socket) -> Optional[Message]:
        logger.debug(f"[{sock.getsockname()}] receiving msg from {sock.getpeername()}.")
        # Receive header
        header_bytes = sock.recv(8)
        resp_len = int.from_bytes(header_bytes, "little")
        logger.debug(f"[{sock.getsockname()}] -> received header: {resp_len=}")

        # Return if no response
        if resp_len == 0:
            return None

        # Receive message
        resp_bytes = cls._recvall(sock, resp_len)

        # Decode
        msg = cls.decode(resp_bytes)
        logger.info(f"[{sock.getsockname()}] received message: {msg=} from {sock.getpeername()}")
        return msg

    @classmethod
    def send(cls, message: Message, target: Target) -> Optional[Message]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            logger.debug(f"[{sock.getsockname()}] connecting to {target.address}...")
            sock.connect(target.address)
            logger.debug(f"[{sock.getsockname()}] connected to {target.address}.")

            # Send message
            cls._send(sock, message)

            # Receive response
            response = cls._receive(sock)

        return response


class MessageHandler(BaseRequestHandler, MessageSender):

    @property
    def handlers(self) -> Dict[MessageType, Callable[[Message, Target], None]]:
        return {}
    
    @property
    def contact_address(self) -> ADDRESS:
        """Address at which this this handler is contacted."""
        return self.request.getsockname()

    def handle(self) -> None:
        # Receive message
        sender = Target(None, self.client_address[1])
        msg = self._receive(self.request)

        # handle message
        try:
            handler = self.handlers[msg.type]
            handler(msg, sender)
        except KeyError:
            print(
                f"Recieved message of unknown type `{msg.type}`."
                f"Can only handle {self.handlers.keys()}."
            )
        
        logger.debug(f"[{self.request.getsockname()}] -> done handling")

    def reply(self, msg: Message) -> None:
        """Send reply."""
        self._send(self.request, msg)
