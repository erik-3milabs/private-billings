import sys
from src.private_billing.server.market_config import MarketConfig
from src.private_billing import (
    launch_market_operator,
    launch_peer,
    launch_billing_server,
)

if __name__ == "__main__":
    mc = MarketConfig("0.0.0.0", 5555, 5554, 5553)

    type_ = sys.argv[1]
    match type_:
        case "bill":
            launch_billing_server(mc, ip="0.0.0.0")
        case "peer":
            launch_peer(mc, ip="0.0.0.0")
        case "market":
            launch_market_operator(mc, ip="0.0.0.0")
        case _:
            raise ValueError(f"{type_} is invalid type")
