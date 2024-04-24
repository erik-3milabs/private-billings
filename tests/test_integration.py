from private_billing.core import (
    Bill,
    SharedBilling,
    ClientID,
    CycleContext,
    Data,
    HiddenBill,
    HiddenData,
    HidingContext,
    Int64ToFloatConvertor,
    SharedMaskGenerator,
    Flag,
    vector,
)


class TestIntegration:

    def get_cycle_context(self):
        cycle_length = 2048
        retail_prices = vector([0.21] * cycle_length)
        trading_prices = vector([0.11] * cycle_length)
        feed_in_tarifs = vector([0.05] * cycle_length)
        return CycleContext(
            0, cycle_length, retail_prices, feed_in_tarifs, trading_prices
        )

    def get_mask_generators(self, client_ids):
        conv = Int64ToFloatConvertor(4, 4)
        generators = {c: SharedMaskGenerator(conv) for c in client_ids}

        # Exchange seeds
        for c1, g1 in generators.items():
            for c2, g2 in generators.items():
                if c1 == c2:
                    # exclude self
                    continue

                s1 = g1.get_seed_for_peer(c2)
                s2 = g2.get_seed_for_peer(c1)

                g1.consume_foreign_seed(s2, c2)
                g2.consume_foreign_seed(s1, c1)

        return generators

    def generate_hiding_contexts(self, cyc, generators):
        hcs = {c: HidingContext(cyc, g) for c, g in generators.items()}
        return hcs

    def generate_data(self, client_ids, cyc: CycleContext):
        data = {}
        for i, c in enumerate(client_ids):
            is_consumer: Flag = c % 2 == 0
            is_producer: Flag = 1 - is_consumer

            data[c] = Data(
                client=c,
                cycle_id=0,
                consumptions=vector([is_consumer * i] * cyc.cycle_length),
                consumption_promise=vector([is_consumer * i] * cyc.cycle_length),
                supplies=vector([is_producer * i] * cyc.cycle_length),
                supply_promise=vector(vector([is_producer * i] * cyc.cycle_length)),
                accepted_flags=vector([1] * cyc.cycle_length),
            )

        return data

    def hide_data(
        self,
        hiding_contexts: dict[ClientID, SharedMaskGenerator],
        data: dict[ClientID, Data],
    ) -> dict[ClientID, HiddenData]:
        hidden_data = {}
        for c, d in data.items():
            hc = hiding_contexts[c]
            hidden_data[c] = d.hide(hc)

        return hidden_data

    def compute_bills(self, hidden_data: dict[ClientID, HiddenData], cyc: CycleContext):
        sb = SharedBilling()
        sb.record_contexts(cyc)
        for c, d in hidden_data.items():
            sb.record_data(d, c)

        # Compute bills
        return sb.compute_bills(0)

    def unhide_bills(
        self,
        hidden_bills: dict[ClientID, HiddenBill],
        hiding_contexts: dict[ClientID, HidingContext],
    ):
        plain_bills = {}
        for c, hb in hidden_bills.items():
            hc = hiding_contexts[c]
            plain_bills[c] = hb.reveal(hc)

        return plain_bills

    def compute_expected_bills(
        self, client_data: dict[ClientID, Data], cyc: CycleContext
    ) -> dict[ClientID, Bill]:
        # Compute total deviations
        total_deviations = vector.new(cyc.cycle_length)
        for c, d in client_data.items():
            total_deviations += d.get_individual_deviations()

        bills = {}
        for c, d in client_data.items():

            results = []
            for accepted, rp, tp, fit, cons, sup, td, indiv_dev in zip(
                d.accepted_flags,
                cyc.retail_prices,
                cyc.trading_prices,
                cyc.feed_in_tarifs,
                d.consumptions,
                d.supplies,
                total_deviations,
                d.get_individual_deviations(),
            ):
                if accepted:
                    if td == 0:
                        bill = cons * tp
                        reward = sup * tp
                    if td < 0:
                        if indiv_dev <= 0:
                            bill = cons * tp
                        else:
                            bill = cons * tp + (indiv_dev * (rp - tp))
                        reward = sup * tp
                    if td > 0:
                        bill = cons * tp
                        if indiv_dev <= 0:
                            reward = sup * tp
                        else:
                            reward = sup * tp + (indiv_dev * (fit - rp))
                else:
                    bill = cons * rp
                    reward = sup * fit

                results.append((bill, reward))

            # Convert results to bill
            bill = [b for (b, _) in results]
            rewards = [r for (_, r) in results]

            bills[c] = Bill(cyc.cycle_id, bill, rewards)

        return bills

    def check_bills(
        self, bills: dict[ClientID, Bill], expected_bills: dict[ClientID, Bill]
    ):
        for c, b in bills.items():
            eb = expected_bills[c]

            is_consumer = c % 2 == 0

            if is_consumer:
                assert b.bill == eb.bill
            else:
                assert b.reward == eb.reward

    def test_integration(self):
        cyc = self.get_cycle_context()

        # Create multiple clients
        client_ids = list(range(10))
        generators = self.get_mask_generators(client_ids)
        hcs = self.generate_hiding_contexts(cyc, generators)

        # Generate data
        client_data = self.generate_data(client_ids, cyc)
        hidden_client_data = self.hide_data(hcs, client_data)

        # Compute bills
        hidden_bills = self.compute_bills(hidden_client_data, cyc)
        plain_bills = self.unhide_bills(hidden_bills, hcs)

        expected_bills = self.compute_expected_bills(client_data, cyc)

        self.check_bills(plain_bills, expected_bills)
