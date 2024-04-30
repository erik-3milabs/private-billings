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
logger.setLevel(logging.DEBUG)


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


@dataclass
class Target:
    id: UUID
    address: tuple[str, int]

    @property
    def ip(self):
        return self.address[0]

    @property
    def port(self):
        return self.address[1]


class MessageHandler(BaseRequestHandler):
    
    @property
    def handlers(self) -> Dict[MessageType, Callable[[Message, Target], None]]:
        return {}

    def handle(self) -> None:
        # Convert bytes to message
        data = self.request.recv(1024).strip()
        msg: Message = pickle.loads(data)
        sender = Target(None, self.client_address)
        
        logger.debug(f"received: {msg}")

        # handle message
        try:
            handler = self.handlers.get(msg.type)
            handler(msg, sender)
        except IndexError:
            print(f"Recieved message of unknown type `{msg.type}`.")

    def reply(self, msg: Message) -> None:
        self.request.sendall(pickle.dumps(msg))
        logger.debug(f"sent: {msg}")


class MessageSender:

    @staticmethod
    def send(message: Message, target: Target) -> Optional[Message]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(target.address)

            # Send
            msg_bytes = pickle.dumps(message)
            sock.sendall(msg_bytes)
            logger.debug(f"sent: {message}")

            # Receive
            resp_bytes = sock.recv(1024)
            if len(resp_bytes) > 0:
                resp = pickle.loads(resp_bytes)
                logger.debug(f"received: {resp}")
            else:
                resp = None

        return resp
