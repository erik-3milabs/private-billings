# Private Billings

This repository provides a proof-of-concept library that acts as a framework for performing privacy-preserving billing in peer-to-peer energy trading markets.
Additionally, this library contains a default implementation of the [UCS](docs/universal_cost_split.md) [billing model](docs/billing_model.md).

## Documentation
Documentation for this library can be found [here](docs/docs.md).

## Installation
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
and you should be good to go!