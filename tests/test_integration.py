import random
from threading import Thread
from time import sleep
from typing import Tuple

import zmq
from src.private_billing import CoreServer, EdgeServer
from src.private_billing.core import Bill, CycleContext, Data, vector
from src.private_billing.messages import (
    BillMessage,
    HiddenBillMessage,
    ContextMessage,
    DataMessage,
    GetBillMessage,
)
from src.private_billing.server import TCPAddress, PickleEncoder


class TestIntegration:
    
    def launch_edge(self, address, cyc_len) -> Tuple[EdgeServer, Thread]:
        edge = EdgeServer(address, cyc_len)
        thread = Thread(target=edge.start)
        thread.start()
        print(f"Running edge on {address}.")
        return edge, thread

    def launch_core(self, address, edge_address) -> Tuple[CoreServer, Thread]:
        core = CoreServer(address)
        thread = Thread(target=core.start, args=(edge_address,))
        thread.start()
        print(f"Running core on {address}.")
        return core, thread

    def send(self, msg, target: TCPAddress) -> None:
        ctxt = zmq.Context()
        sock = ctxt.socket(zmq.REQ)
        with sock.connect(str(target)):
            enc = PickleEncoder.encode(msg)
            sock.send(enc)
            sock.recv()

    def test_integration(self):
        cycle_len = 1024
        nr_cores = 10
        port_range = list(range(5000, 6000))
        ports = random.choices(port_range, k=nr_cores + 1)

        # Parties
        edge_address = TCPAddress("localhost", ports[0])
        edge = self.launch_edge(edge_address, cycle_len)
        core_ports = ports[1:]
        cores = [self.launch_core(TCPAddress("localhost", port), edge_address) for port in core_ports]

        # Distribute cycle context
        cyc = CycleContext(
            0,
            cycle_len,
            vector.new(cycle_len, 0.21),
            vector.new(cycle_len, 0.05),
            vector.new(cycle_len, 0.11),
        )
        cyc_msg = ContextMessage(None, cyc)
        self.send(cyc_msg, edge_address)
        
        # Allow all to settle in
        sleep(1)

        # Have peers send data to billing server
        for idx, port in enumerate(core_ports):
            target = TCPAddress("localhost", port)

            # Generate random data
            data = Data(None, 0, vector.new(cycle_len, idx), vector.new(cycle_len, idx))

            # Send data
            data_msg = DataMessage(None, data)
            self.send(data_msg, target)
            print(f"sent data {idx}:{port}")

        # Wait it out
        sleep(5)

        # Get bill from peers
        for idx, (core, _) in enumerate(cores):
            target = TCPAddress("localhost", port)
            
            # is_ready = False
            # while not is_ready:
            #     is_ready = 0 in core.bills
            bill = core.bills[0]
            
            # Test bill correctness
            assert isinstance(bill.bill, vector)
            assert bill.bill == vector.new(1024, idx * 0.11)
            assert isinstance(bill.reward, vector)
            assert bill.reward == vector.new(1024)

        # Stop all threads
        server, thread = edge
        server.terminate()
        thread.join()

        for peer in cores:
            server, thread = peer
            server.terminate()
            thread.join()
