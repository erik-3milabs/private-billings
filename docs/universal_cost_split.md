# Universal Cost Split
The peer-to-peer trading process typically consists of four phases:
- **forecast**; each peer creates a prediction of their energy consumption / production for the coming period.
- **auction**; each peer offers / bids for energy. The auction sets a trading price and connects the offers to the bids.
- **utilization**; during the predetermined period, each peer consumes / delivers energy.
- **billing**; each peer is billed / rewarded for their consumption / production.

This demosntrates that energy is traded (auctioned) _before_ it is produced/consumed.
The offers/bids generated for the auction rely on imperfect forecasts, which leads to discrepancies between what was promised in the auction phase and what was actually delivered/consumed in the utilization phase.
The Universal Cost Split (UCS) billing model attempts to resolves these discrepancies in the billing phase.

In Universal Cost Split (UCS), the cost incurred by these discrepancies are equally spread among those contributing to the discrepancy.
That is: if more energy was produced than promised, the loss in revenue is carried equally among those that produced too much; if too much energy was consumed, the cost associated with purchasing the extra energy is spread uniformly over the overconsumers.

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

In this library, this billing algorithm is implemented in the [`HiddenData.compute_hidden_bill` function](../src/private_billing/core/hidden_data.py).