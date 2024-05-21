import sys
from src.private_billing import (
    launch_market_operator,
    launch_peer,
    launch_billing_server,
)

if __name__ == "__main__":
    type_ = sys.argv[1]

    # Settings
    host = "0.0.0.0"
    market_address = host, 5555
    billing_address = host, 5554
    cyc_len = 672  # nr of 15m slots in a week.
    
    match type_:
        case "bill":
            launch_billing_server(billing_address, market_address)
        case "peer":
            port = sys.argv[2]
            server_address = host, int(port)
            launch_peer(server_address, market_address)
        case "market":
            launch_market_operator(market_address, cyc_len)
        case _:
            raise ValueError(f"{type_} is invalid type")
