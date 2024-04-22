import itertools
import pytest
from private_billing import SharedMaskGenerator, ClientID
from .test_utils import get_test_converter


class TestSharedMaskGenerator:

    def get_generator(self) -> SharedMaskGenerator:
        peer: ClientID = 0
        g = SharedMaskGenerator(get_test_converter())
        g.get_seed_for_peer(peer)
        g.consume_foreign_seed(42, peer)
        return g

    def get_generator_group(self) -> dict[ClientID, SharedMaskGenerator]:
        group_size = 10
        generator_map = {
            id: SharedMaskGenerator(get_test_converter()) for id in range(group_size)
        }

        for (c1, g1), (c2, g2) in itertools.combinations(generator_map.items(), 2):
            s1 = g1.get_seed_for_peer(c2)
            s2 = g2.get_seed_for_peer(c1)
            g1.consume_foreign_seed(s2, c2)
            g2.consume_foreign_seed(s1, c1)

        return generator_map

    def test_cannot_sample_generator_without_seeds(self):
        g = SharedMaskGenerator(get_test_converter())
        with pytest.raises(AssertionError):
            g.generate_mask(iv=0)

    def test_iv_makes_masking_deterministic(self):
        g = self.get_generator()
        val1 = g.generate_mask(iv=0)
        val2 = g.generate_mask(iv=0)
        assert val1 == val2

        val1 = g.generate_mask(iv=42)
        val2 = g.generate_mask(iv=42)
        assert val1 == val2

    def test_different_iv_gives_different_value(self):
        g = self.get_generator()
        val1 = g.generate_mask(iv=0)
        val2 = g.generate_mask(iv=1)
        assert val1 != val2

    def test_shares_sum_to_zero(self):
        gg = self.get_generator_group()
        
        iv = 42
        masks = [
            g.generate_mask(iv)
            for g in gg.values()
        ]
        
        assert sum(masks) == 0