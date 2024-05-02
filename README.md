# Private Billings

This repository provides a proof-of-concept implementation of the [private billings project](todo).
This project enables computing bills and rewards for peers trading energy in a peer-to-peer trading market in such a way that all trading information remains hidden to all parties involved (except the parties owning the data).
This implementation assumes all parties involved in the billing process fit the honest-but-curious attack-model; all parties follow the protocol, yet are eager to find out private information on the other participants in the trading market.

# Installation
Installation involves the following steps:
1. Install OpenFHE-development, following its [installation procedure](https://openfhe-development.readthedocs.io/en/latest/sphinx_rsts/intro/installation/installation.html).

2. Install OpenFHE-python, following its [installation procedure](https://github.com/openfheorg/openfhe-python/tree/main?tab=readme-ov-file#linux).
Afterwards, make sure to add the installation file to your PYTHONPATH.
```sh
export PYTHONPATH=/path/to/OPENFHE_so_files:$PYTHONPATH
```

3. (recommended) Setup a virtual environment.
```
python3 -m venv .env
```

4. Install this package
```sh
git clone git@github.com:3MI-Labs/private-billings.git
python3 -m pip install -e private-billings
```

## Structure
The source of the package is found in [here](./src/private_billing/); the test-suite is found [here](./tests).
