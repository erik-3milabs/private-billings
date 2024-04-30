# Private Billings

This repository provides a proof-of-concept implementation of the [private billings project](todo).
This project enables computing bills and rewards for peers trading energy in a peer-to-peer trading market in such a way that all trading information remains hidden to all parties involved (except the parties owning the data).
This implementation assumes all parties involved in the billing process fit the honest-but-curious attack-model; all parties follow the protocol, yet are eager to find out private information on the other participants in the trading market.

## Structure
The source of the package is found in [here](./src/private_billing/); the test-suite is found [here](./tests).
