# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto
import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P  # noqa: F401
from faebryk.libs.picker.picker import DescriptiveProperties

from .texas_instruments_tpsm86837rcgr import TEXAS_INSTRUMENTS_TPSM86837RCGR

logger = logging.getLogger(__name__)


class TexasInstrumentsTPSM86837RCGR_ReferenceDesign(Module):
    """
    Power Management Modules 4.5V to 28V input voltage, 8A ECO mode,
    synchronous buck module with QFN package
    """

    # ----------------------------------------
    #               modules
    # ----------------------------------------
    power_module: TEXAS_INSTRUMENTS_TPSM86837RCGR

    # ----------------------------------------
    #              interfaces
    # ----------------------------------------
    power_in = L.d_field(lambda: F.ElectricPower())  # .make_sink())
    power_out = L.d_field(lambda: F.ElectricPower())  # .make_source())
    enable: F.EnablePin
    power_good: F.ElectricLogic

    # ----------------------------------------
    #               parameters
    # ----------------------------------------

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    @L.rt_field
    def bridge(self):
        return F.can_bridge_defined(self.power_in, self.power_out)

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self, gnd_only=True)
        )

    def __preinit__(self):
        # ------------------------------------
        #           connections
        # ------------------------------------
        # only connect through the following interfaces for ease of use
        self.power_module.power_in.connect(self.power_in)
        self.power_module.power_out.connect(self.power_out)
        self.power_module.enable.connect(self.enable)
        self.power_module.power_good.connect(self.power_good)

        # enable the power module
        self.power_good.set_weak(on=True, owner=self).resistance.constrain_subset(
            L.Range.from_center_rel(100 * P.kohm, 0.10)
        )

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        # self.enable.make_required()
        for cap in self.power_in.decoupled.decouple(owner=self, count=2).capacitors:
            cap.capacitance.constrain_subset(L.Range.from_center_rel(10 * P.uF, 0.1))

        # use the recommended outputcapacitors from the datasheet
        for cap in self.power_out.decoupled.decouple(owner=self, count=3).capacitors:
            cap.add(
                F.has_descriptive_properties_defined(
                    {
                        DescriptiveProperties.manufacturer: "Murata Electronics",
                        DescriptiveProperties.partno: "GRM32ER71E226KE15L",
                    }
                )
            )
            # cap.add(F.has_descriptive_properties_defined({"LCSC": "C21397"}))
