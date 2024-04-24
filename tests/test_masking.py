import itertools
import pytest
from private_billing import SharedMaskGenerator, ClientID, Int64ToFloatConvertor, vector
from .test_utils import get_test_convertor


class TestSharedMaskGenerator:

    def get_generator(self) -> SharedMaskGenerator:
        peer: ClientID = 0
        g = SharedMaskGenerator(get_test_convertor())
        g.get_seed_for_peer(peer)
        g.consume_foreign_seed(42, peer)
        return g

    def get_generator_group(self) -> dict[ClientID, SharedMaskGenerator]:
        group_size = 10
        generator_map = {
            id: SharedMaskGenerator(get_test_convertor()) for id in range(group_size)
        }

        for (c1, g1), (c2, g2) in itertools.combinations(generator_map.items(), 2):
            s1 = g1.get_seed_for_peer(c2)
            s2 = g2.get_seed_for_peer(c1)
            g1.consume_foreign_seed(s2, c2)
            g2.consume_foreign_seed(s1, c1)

        return generator_map

    def test_cannot_sample_generator_without_seeds(self):
        g = SharedMaskGenerator(get_test_convertor())
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
        iv = 42
        gg = self.get_generator_group()
        masks = [g.generate_mask(iv) for g in gg.values()]
        assert sum(masks) == 0

    def test_share_vectors_sum_to_zero(self):
        iv = 42
        gg = self.get_generator_group()
        masks = [g.generate_masks(iv, 1024) for g in gg.values()]
        assert sum(masks, vector.new(1024)) == vector.new(1024)


class TestSharedMaskingAndConversion:

    def get_generator_group(self) -> dict[ClientID, SharedMaskGenerator]:
        group_size = 10
        generator_map = {
            id: SharedMaskGenerator(Int64ToFloatConvertor(4, 4))
            for id in range(group_size)
        }

        for (c1, g1), (c2, g2) in itertools.combinations(generator_map.items(), 2):
            s1 = g1.get_seed_for_peer(c2)
            s2 = g2.get_seed_for_peer(c1)
            g1.consume_foreign_seed(s2, c2)
            g2.consume_foreign_seed(s1, c1)

        return generator_map

    def test_share_vectors_sum_to_zero(self):
        gg = self.get_generator_group()
        g = gg[0]

        iv = 42
        masks = [g.generate_masks(iv, 1024) for g in gg.values()]

        assert g.unmask(masks) == vector.new(1024)
