from abc import ABC
from dataclasses import dataclass
from enum import Enum
import pickle
import socket
from socketserver import BaseRequestHandler
from typing import Callable, Dict, Optional
from uuid import UUID

import logging

logger = logging.getLogger(__name__)
logging.basicConfig(filename='application.log', level=logging.DEBUG)


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


@dataclass
class Target:
    id: UUID
    address: tuple[IP, int]

    @property
    def ip(self):
        return self.address[0]

    @property
    def port(self):
        return self.address[1]


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
        # Encode message
        enc_msg = cls.encode(message)

        # Send header
        msg_len = len(enc_msg)        
        msg_len_bytes = msg_len.to_bytes(8, 'little')
        logger.debug(f"sending header: {msg_len_bytes=}")
        sock.send(msg_len_bytes)
        
        # Send content
        if msg_len > 0:
            logger.debug(f"sending message")
            sock.sendall(enc_msg)

    @classmethod
    def _receive(cls, sock: socket.socket) -> Optional[Message]:
        # Receive header
        header_bytes = sock.recv(8)
        resp_len = int.from_bytes(header_bytes, 'little')
        logger.debug(f"received header: {resp_len}")
        
        # Return if no response
        if resp_len == 0:
            return None
        
        # Receive message
        nr_messages = resp_len // 16384 + 1
        resp_bytes = bytes()
        for _ in range(nr_messages):
            resp_bytes += sock.recv(16384)
        logger.debug("received message")

        # Decode
        msg = cls.decode(resp_bytes)
        return msg
        

    @classmethod
    def send(cls, message: Message, target: Target) -> Optional[Message]:
        logger.debug(f"sending: {message} to {target}")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(target.address)
            logger.debug(f"connected to {target.address}.")
            
            # Send message
            cls._send(sock, message)
            logger.debug(f"message sent.")
            
            # Receive response
            response = cls._receive(sock)

        return response

class MessageHandler(BaseRequestHandler, MessageSender):

    @property
    def handlers(self) -> Dict[MessageType, Callable[[Message, Target], None]]:
        return {}

    def handle(self) -> None:
        # Receive message
        msg = self._receive(self.request)
        sender = Target(None, self.client_address)
        logger.debug(f"received: {msg} from {sender}")

        # handle message
        try:
            handler = self.handlers.get(msg.type)
            handler(msg, sender)
        except IndexError:
            print(f"Recieved message of unknown type `{msg.type}`.")

    def reply(self, msg: Message) -> None:
        """Send reply."""
        self._send(self.request, msg)
