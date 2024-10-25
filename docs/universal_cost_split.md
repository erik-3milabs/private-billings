# Universal Cost Split
The Universal Cost Split (UCS) is an instance of a [billing model](billing_model.md) introduced by XXXX, XXXX and XXXX [1] at XXXX.
In UCS, the cost incurred by discrepancies between the auction and utilization phase are uniformly divided among those contributing to the discrepancy.
That is: if more energy was produced than promised, the excess energy is sold to the energy supplier for the (low) feed-in tarif.
The loss incurred from not being able to trade for (the higher) trading price, is carried equally among those that produced too much.
Similarly, if too much energy was consumed, the cost associated with purchasing the extra energy is spread uniformly over the overconsumers.

We provide a pseudo-code representation of the billing model below:
```
if accepted for trading:
    bill = consumption * trading price
    reward = production * trading price

    if total deviation < 0 and individual deviation > 0:
        bill += (retail price - trading price) * (- total deviation) / #(accepted consumers w/ positive individual deviation)

    if total deviation > 0 and individual deviation > 0:
        reward -= (trading price - feed-in tarif) * total deviation / #(accepted prosumers w/ positive individual deviation)
else:
    bill = consumption * retail price
    reward = production * feed-in tarif
```

Here, the `total deviation` is computed as the sum of the `individual deviation` of all peers.
The `individual deviation` of a peer is the difference between their promised consumption/production and what actually happens.

## Drawbacks
There are two significant restrictions to this model.
1. The model is not zero-sum. The model provides an unreasonable solution in case of mass-scale underconsumption or underproduction.
2. The model implicitly requires all producers in the network have a comparable production capacity. In networks where this is not the case, a small overproducer could receive a _negative_ reward when they have to contribute to a larger peer also overproducing.

Before utilizing this model, one should be confident these two cases will not occur/are dealt with.

## Implementation
In this library, this billing algorithm is implemented in the [`HiddenData.compute_hidden_bill` function](../src/private_billing/core/hidden_data.py).
This implementation assumes all parties involved in the billing process fit the honest-but-curious attack-model; all parties follow the protocol, yet are eager to find out private information on the other participants in the trading market.

### Footnotes
XXXX
