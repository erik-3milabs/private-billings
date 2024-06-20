import sys
import zmq
from src.private_billing.core import Data, vector, CycleContext
from src.private_billing.server import PickleEncoder, TCPAddress
from src.private_billing.messages import ContextMessage, DataMessage

ctxt = zmq.Context()
sock = ctxt.socket(zmq.REQ)

def send(msg, address: TCPAddress):
    with sock.connect(str(address)):
        enc = PickleEncoder.encode(msg)
        sock.send(enc)
        repl = sock.recv()
    return PickleEncoder.decode(repl)

def send_context(cycle_id, cyclen, address) -> None:
    ctxt = CycleContext(
        cycle_id,
        cyclen,
        vector.new(cyclen, 0.21),
        vector.new(cyclen, 0.05),
        vector.new(cyclen, 0.11),
    )
    msg = ContextMessage(None, ctxt)
    send(msg, address)


def broadcast_data(cycle_id, cyclen, addresses) -> None:
    for idx, address in enumerate(addresses):
        data = Data(None, cycle_id, vector.new(cyclen, idx + 1), vector.new(cyclen, idx + 2))
        msg = DataMessage(None, data)
        send(msg, address)
            
            
if __name__ == "__main__":
    args = sys.argv + [None] * 10
    cycle_id = int(args[1] or 0)
    cyclen = int(args[2] or 672)
    
    edge_port = 5555
    edge_address = TCPAddress("localhost", edge_port)
    ports = list(range(5560, 5565))
    addresses = list(map(lambda x: TCPAddress("localhost", x), ports))
    
    send_context(cycle_id, cyclen, edge_address)
    broadcast_data(cycle_id, cyclen, addresses)
    
