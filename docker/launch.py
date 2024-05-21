import sys
from src.private_billing import (
    launch_market_operator,
    launch_peer,
    launch_billing_server,
)

if __name__ == "__main__":
    type_ = sys.argv[1]
    
    # market address
    market_host = sys.argv[2]
    market_port = int(sys.argv[3])
    market_address = market_host, market_port
    
    # server host
    host = sys.argv[4]

    # Settings
    cyc_len = 672  # nr of 15m slots in a week.
    
    match type_:
        case "bill":
            server_address = host, 5554
            launch_billing_server(server_address, market_address)
        case "peer":
            port = sys.argv[5]
            server_address = host, int(port)
            launch_peer(server_address, market_address)
        case "market":
            server_address = host, 5555
            launch_market_operator(server_address, cyc_len)
        case _:
            raise ValueError(f"{type_} is invalid type")
