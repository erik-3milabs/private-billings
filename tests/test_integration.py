import random
import socket
from socketserver import TCPServer
from threading import Thread
from time import sleep
from typing import Tuple
from src.private_billing.core import Bill, CycleContext, Data, vector
from src.private_billing import (
    BillingServer,
    BillingServerDataStore,
    Peer,
    PeerDataStore,
    MarketOperator,
    MarketOperatorDataStore,
)
from src.private_billing.messages import (
    BillMessage,
    BootMessage,
    ContextMessage,
    DataMessage,
    GetBillMessage,
    GetContextMessage,
)
from src.private_billing.server import MessageSender, Target, MarketConfig


class TestIntegration:

    def launch_boot_thread(self, mc, address):
        sleep(0.5)
        boot = BootMessage(mc)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(address)
            MessageSender._send(sock, boot)

    def launch_market_operator(self, mc: MarketConfig) -> Tuple[TCPServer, Thread]:
        address = mc.market_host, mc.market_port
        operator = TCPServer(address, MarketOperator)

        # Configure server
        mods = MarketOperatorDataStore()
        mods.market_config = mc
        mods.cycle_length = 1024
        operator.data = mods

        print(f"Running operator on {operator.server_address}.")
        thread = Thread(target=operator.serve_forever)
        thread.start()
        return operator, thread

    def launch_billing_server(self, mc: MarketConfig) -> Tuple[TCPServer, Thread]:
        address = "localhost", mc.billing_port
        server = TCPServer(address, BillingServer)

        # Configure server
        bsds = BillingServerDataStore()
        bsds.market_config = mc
        server.data = bsds

        # Launch
        print(f"Running server on {server.server_address}.")
        thread = Thread(target=server.serve_forever)
        thread.start()
        return server, thread

    def launch_peer(self, mc: MarketConfig, port) -> Tuple[TCPServer, Thread]:
        address = "localhost", port
        peer = TCPServer(address, Peer)

        # Configure server
        pds = PeerDataStore()
        pds.market_config = mc
        peer.data = pds

        # Launch peer
        print(f"Launching peer on {peer.server_address}.")
        thread = Thread(target=peer.serve_forever)
        thread.start()
        return peer, thread

    def test_integration(self):
        nr_peers = 10
        port_range = list(range(5000, 6000))
        ports = random.choices(port_range, k=nr_peers + 2)
        mc = MarketConfig("localhost", ports[0], ports[1], None)

        # Parties
        market_operator = self.launch_market_operator(mc)
        billing_server = self.launch_billing_server(mc)
        peer_ports = ports[2:]
        peers = [self.launch_peer(mc, port) for port in peer_ports]

        # Send boot messages
        print("giving boot signals")
        boot = BootMessage(mc)
        for port in ports[1:]:
            target = Target(None, ("localhost", port))
            resp = MessageSender.send(boot, target)
            print(port, resp)

        # Distribute cycle context
        cycle_len = 1024
        cyc = CycleContext(
            0,
            cycle_len,
            vector.new(cycle_len, 0.21),
            vector.new(cycle_len, 0.05),
            vector.new(cycle_len, 0.11),
        )
        cyc_msg = ContextMessage(cyc)
        target = Target(None, (mc.market_host, mc.market_port))
        MessageSender.send(cyc_msg, target)

        # Have peers send data to billing server
        for idx, port in enumerate(peer_ports):
            target = Target(None, ("localhost", port))

            # Request cycle context
            gc_msg = GetContextMessage(0)
            resp: ContextMessage = MessageSender.send(gc_msg, target)
            context = resp.context

            # Generate random data
            cycle_len = context.cycle_length
            data = Data(None, 0, vector.new(cycle_len, idx), vector.new(cycle_len, idx))

            # Send data
            print(f"send data {idx}:{port}")
            data_msg = DataMessage(data)
            resp = MessageSender.send(data_msg, target)

        # Get bill from peers
        for idx, port in enumerate(peer_ports):
            target = Target(None, ("localhost", port))

            # Request bill
            msg = GetBillMessage(0)
            received = False
            while not received:
                resp: BillMessage = MessageSender.send(msg, target)
                received = resp.bill != None

            # Test bill correctness
            assert isinstance(resp, BillMessage)
            assert isinstance(resp.bill, Bill)
            assert isinstance(resp.bill.bill, vector)
            assert resp.bill.bill == vector.new(1024, idx * 0.11)
            assert isinstance(resp.bill.reward, vector)
            assert resp.bill.reward == vector.new(1024)

        # Stop all threads
        server, thread = market_operator
        server.shutdown()
        thread.join()

        server, thread = billing_server
        server.shutdown()
        thread.join()

        for peer in peers:
            server, thread = peer
            server.shutdown()
            thread.join()
