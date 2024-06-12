import sys
from src.private_billing.server import TCPAddress
from src.private_billing import launch_core, launch_edge

if __name__ == "__main__":
    args = sys.argv + [None] * 2

    # Settings
    host = "0.0.0.0"
    market_address = TCPAddress(host, 5555)

    type_ = args[1]
    match type_:
        case "edge":
            launch_edge(market_address)
        case "core":
            port = int(args[2] or 5556)
            server_address = TCPAddress(host, port)
            launch_core(server_address, market_address)
        case _:
            raise ValueError(f"{type_} is invalid type")
