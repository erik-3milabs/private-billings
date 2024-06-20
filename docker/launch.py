import os
from src.private_billing.server import TCPAddress
from src.private_billing import launch_core, launch_edge

if __name__ == "__main__":
    server_type = os.environ.get("SERVER_TYPE")
    
    # Edge address settings
    edge_host = os.environ.get("EDGE_HOST", "0.0.0.0")
    edge_port = os.environ.get("EDGE_PORT", 5555)
    edge_address = TCPAddress(edge_host, edge_port)

    match server_type:
        case "edge":
            cyc_len = os.environ.get("CYCLE_LENGTH", 672)
            launch_edge(edge_address, cyc_len)
        case "core":
            core_host = os.environ.get("CORE_HOST", "0.0.0.0")
            core_port = os.environ.get("CORE_PORT", 5556)
            server_address = TCPAddress(core_host, core_port)
            launch_core(server_address, edge_address)
        case _:
            raise ValueError(f"{server_type} is invalid type")
