import pytest
from src.private_billing.core import (
    CycleContext,
    SharedCycleData,
    Data,
    vector,
    PublicHidingContext,
    HidingContext,
)


class HidingContextMock(HidingContext):
    """
    Mock for Hiding Context
    """

    def __init__(self, cycle_len) -> None:
        super().__init__(cycle_len, None)

    def mask(self, values: list[float], iv: int) -> list[float]:
        return values

    def encrypt(self, values: list[float]):
        return values

    def decrypt(self, values: list[float]):
        return values

    def scale(self, ctxt, scalars: vector):
        return ctxt * scalars

    def multiply(self, ctxt_1, ctxt_2):
        return ctxt_1 * ctxt_2

    def invert_flags(self, flags):
        return vector([1 - v for v in flags])

    def get_public_hiding_context(self) -> PublicHidingContext:
        return PublicHidingContextMock(self.cycle_length)


class PublicHidingContextMock(HidingContextMock):
    """
    Public Mock for Hiding Context
    """


CYCLEN = 1
RETAIL_PRICE, FEED_IN_TARIF, TRADING_PRICE = (
    0.21,
    0.05,
    0.11,
)

NR_P2P_CONSUMERS = 7
NR_P2P_PRODUCERS = 3


class TestHiddenBill:

    def create_context(
        self,
        retail_price: float = RETAIL_PRICE,
        feed_in_tarif: float = FEED_IN_TARIF,
        trading_price: float = TRADING_PRICE,
    ) -> CycleContext:
        return CycleContext(
            0,
            CYCLEN,
            vector.new(CYCLEN, retail_price),
            vector.new(CYCLEN, feed_in_tarif),
            vector.new(CYCLEN, trading_price),
        )

    def create_data(self, promise: float, utilization: float) -> Data:
        return Data(
            0,
            1,
            utilization_promises=vector.new(CYCLEN, promise),
            utilizations=vector.new(CYCLEN, utilization),
        )

    def create_shared_cycle_data(
        self, total_dev: float, nr_p2p_consumers: int, nr_p2p_producers: int
    ):
        return SharedCycleData(
            vector.new(CYCLEN, total_dev),
            vector.new(CYCLEN, nr_p2p_consumers),
            vector.new(CYCLEN, nr_p2p_producers),
        )

    def _test(
        self,
        promise: float,
        utilization: float,
        total_dev: float,
        expected_bill: float,
        expected_reward: float,
        cyc: CycleContext = None,
    ) -> None:
        # Create context
        if not cyc:
            cyc = self.create_context()

        # Create shared data
        scd = self.create_shared_cycle_data(
            total_dev, NR_P2P_CONSUMERS, NR_P2P_PRODUCERS
        )

        # Create data
        data = self.create_data(promise, utilization)
        hc = HidingContextMock(cyc.cycle_length)
        hd = data.hide(hc)

        # Compute bill
        bill = hd.compute_hidden_bill(scd, cyc)

        # verify bill
        assert bill.hidden_bill == vector.new(CYCLEN, expected_bill)
        assert bill.hidden_reward == vector.new(CYCLEN, expected_reward)

    def test_compute_hidden_bill_zero(self):
        promise = 0  # no promise -> not accepted for trading
        utilization = 0  # zero -> nothing
        total_dev = 0

        expected_bill = 0
        expected_reward = 0

        self._test(
            promise,
            utilization,
            total_dev,
            expected_bill,
            expected_reward,
        )

    def test_compute_hidden_bill_rejected_consumer(self):
        promise = 0  # no promise -> not accepted for trading
        utilization = 1  # positive -> consumption
        total_dev = 0

        expected_bill = utilization * RETAIL_PRICE
        expected_reward = 0

        self._test(
            promise,
            utilization,
            total_dev,
            expected_bill,
            expected_reward,
        )

    def test_compute_hidden_bill_accepted_consumer_zero_indiv_dev(self):
        promise = 1  # pos promise -> accepted for trading as consumer
        utilization = 1  # positive -> consumption
        total_dev = 0

        expected_bill = utilization * TRADING_PRICE
        expected_reward = 0

        self._test(
            promise,
            utilization,
            total_dev,
            expected_bill,
            expected_reward,
        )

    @pytest.mark.parametrize("total_dev", [0, 17])
    def test_compute_hidden_bill_accepted_consumer_pos_indiv_dev_non_neg_total_dev(
        self, total_dev
    ):
        promise = 1  # pos promise -> accepted for trading as consumer
        utilization = 2  # positive -> consumption

        expected_bill = utilization * TRADING_PRICE
        expected_reward = 0

        self._test(
            promise,
            utilization,
            total_dev,
            expected_bill,
            expected_reward,
        )

    def test_compute_hidden_bill_accepted_consumer_pos_indiv_dev_neg_total_dev(self):
        promise = 1  # pos promise -> accepted for trading as consumer
        utilization = 2  # positive -> consumption
        total_dev = -1

        expected_bill = (
            utilization + total_dev / NR_P2P_CONSUMERS
        ) * TRADING_PRICE - total_dev / NR_P2P_CONSUMERS * RETAIL_PRICE
        expected_reward = 0

        self._test(
            promise,
            utilization,
            total_dev,
            expected_bill,
            expected_reward,
        )

    @pytest.mark.parametrize("total_dev", [-5, 0, 10])
    def test_compute_hidden_bill_accepted_consumer_neg_indiv_dev(self, total_dev):
        promise = 1  # pos promise -> accepted for trading as consumer
        utilization = 0.5  # positive -> consumption

        expected_bill = utilization * TRADING_PRICE
        expected_reward = 0

        self._test(
            promise,
            utilization,
            total_dev,
            expected_bill,
            expected_reward,
        )

    def test_compute_hidden_bill_rejected_producer(self):
        promise = 0  # no promise -> not accepted for trading
        utilization = -1  # negative -> production
        total_dev = 0
        expected_bill = 0
        expected_reward = -utilization * FEED_IN_TARIF

        self._test(
            promise,
            utilization,
            total_dev,
            expected_bill,
            expected_reward,
        )

    def test_compute_hidden_bill_accepted_producer_zero_indiv_dev(self):
        promise = -1  # neg promise -> accepted for trading as producer
        utilization = -1  # negative -> production
        total_dev = 0
        expected_bill = 0
        expected_reward = -utilization * TRADING_PRICE

        self._test(
            promise,
            utilization,
            total_dev,
            expected_bill,
            expected_reward,
        )

    @pytest.mark.parametrize("total_dev", [-13, 0])
    def test_compute_hidden_bill_accepted_producer_pos_indiv_dev_non_pos_tot_dev(
        self, total_dev
    ):
        promise = -1  # neg promise -> accepted for trading as producer
        utilization = -2  # negative -> production, also: overproduction

        expected_bill = 0
        expected_reward = -utilization * TRADING_PRICE

        self._test(
            promise,
            utilization,
            total_dev,
            expected_bill,
            expected_reward,
        )

    def test_compute_hidden_bill_accepted_producer_pos_indiv_dev_pos_tot_dev(self):
        promise = -1  # neg promise -> accepted for trading as producer
        utilization = -2  # negative -> production, also: overproduction
        total_dev = 1

        expected_bill = 0
        expected_reward = (
            -utilization - total_dev / NR_P2P_PRODUCERS
        ) * TRADING_PRICE + total_dev / NR_P2P_PRODUCERS * FEED_IN_TARIF

        self._test(
            promise,
            utilization,
            total_dev,
            expected_bill,
            expected_reward,
        )

    def test_compute_hidden_bill_accepted_producer_pos_tot_dev(self):
        promise = -1  # neg promise -> accepted for trading as producer
        utilization = -3  # negative -> production, also: overproduction
        total_dev = 1

        expected_bill = 0
        expected_reward = (
            -utilization - total_dev / NR_P2P_PRODUCERS
        ) * TRADING_PRICE + total_dev / NR_P2P_PRODUCERS * FEED_IN_TARIF

        self._test(
            promise,
            utilization,
            total_dev,
            expected_bill,
            expected_reward,
        )

    @pytest.mark.parametrize("total_dev", [-33, 0, 7])
    def test_compute_hidden_bill_accepted_producer_neg_indiv_dev(self, total_dev):
        promise = -5  # neg promise -> accepted for trading as producer
        utilization = -3  # negative -> production, also: overproduction

        expected_bill = 0
        expected_reward = -utilization * TRADING_PRICE

        self._test(
            promise,
            utilization,
            total_dev,
            expected_bill,
            expected_reward,
        )

    @pytest.mark.parametrize("total_dev", [-32, 0, 9])
    def test_producer_gone_consumer(self, total_dev):
        promise = -5  # neg promise -> accepted for trading as producer
        utilization = 3  # positive -> consumption

        expected_bill = utilization * RETAIL_PRICE
        expected_reward = 0

        self._test(
            promise,
            utilization,
            total_dev,
            expected_bill,
            expected_reward,
        )

    @pytest.mark.parametrize("total_dev", [-29, 0, 3])
    def test_consumer_gone_producer(self, total_dev):
        promise = 5  # pos promise -> accepted for trading as consumer
        utilization = -3  # negative -> production

        expected_bill = 0
        expected_reward = -utilization * FEED_IN_TARIF

        self._test(
            promise,
            utilization,
            total_dev,
            expected_bill,
            expected_reward,
        )
