from __future__ import annotations
from .hidden_data import HiddenData
from .cycle import CycleContext, CycleID, ClientID
from .hiding import HidingContext
from .utils import Flag, get_positive_flags, mulp_lists, vector
from dataclasses import dataclass


@dataclass
class Data:
    client: ClientID
    cycle_id: CycleID
    consumptions: vector[float]
    supplies: vector[float]
    consumption_promise: vector[float]
    supply_promise: vector[float]
    accepted_flags: vector[Flag]
    
    def hide(self, hc: HidingContext) -> HiddenData:
        """
        Hide the data in this object.
        This is achieved by either encrypting or masking it.
        """
        # Generate p2p_consumer flags
        p2p_consumptions = mulp_lists(self.consumptions, self.accepted_flags)
        p2p_consumer_flags = get_positive_flags(p2p_consumptions)

        # Generate p2p_prosumer flags
        p2p_productions = mulp_lists(self.supplies, self.accepted_flags)
        p2p_producer_flags = get_positive_flags(p2p_productions)

        positive_deviation_flags = self.get_positive_deviation_flags()

        return HiddenData(
            self.client,
            self.cycle_id,
            hc.encrypt(self.consumptions),
            hc.encrypt(self.supplies),
            hc.encrypt(self.accepted_flags),
            hc.encrypt(positive_deviation_flags),
            hc.mask(self.get_individual_deviations(), 0),
            hc.mask(p2p_consumer_flags, 1),
            hc.mask(p2p_producer_flags, 2),
            hc.get_public_hiding_context(),
        )
    
    def check_validity(self, cyc: CycleContext) -> None:
        """
        Check validity of this cycle data

        :param cyc: context to check against
        :raises: AssertionError when invalid
        """
        assert cyc.cycle_id == self.cycle_id
        
        # Check vector lengths are correct
        assert len(self.consumptions) == cyc.cycle_length
        assert len(self.supplies) == cyc.cycle_length
        assert len(self.consumption_promise) == cyc.cycle_length
        assert len(self.supply_promise) == cyc.cycle_length
        assert len(self.accepted_flags) == cyc.cycle_length
        
        # Check either production or consumption is zero; 
        # cannot both be non-zero
        for p, c in zip(self.supplies, self.consumptions):
            assert p == 0 or c == 0

    
    def get_individual_deviations(self) -> vector[float]:
        """
        Compute individual deviations.
        
        Deviations are only relevant when client is accepted for trading
        in a timeslot. Therefore, it is computed as zero otherwise.
        
        Deviation is computed as the supply deviation minus the consumption
        deviation.        
        """
        supply_deviations = self.supplies - self.supply_promise
        consumption_deviations = self.consumptions - self.consumption_promise
        individual_deviations = supply_deviations - consumption_deviations
        
        # set deviation to zero in timeslots where trading is not accepted.
        individual_deviations *= self.accepted_flags
        
        return vector(individual_deviations)    
    

    def get_positive_deviation_flags(self) -> vector[float]:
        """
        Compute positive deviation flags.
        """
        supply_deviations = self.supplies - self.supply_promise
        consumption_deviations = self.consumptions - self.consumption_promise
        return get_positive_flags(supply_deviations + consumption_deviations)
