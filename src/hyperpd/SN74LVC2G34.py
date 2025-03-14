# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P  # noqa: F401
from faebryk.libs.picker.picker import DescriptiveProperties

logger = logging.getLogger(__name__)


class SN74LVC2G34(Module):
    """
    The SN74LVC2G34 is a high performance dual buffer operating
    from a 1.65 to 5.5 V supply. This device is fabricated with
    advanced CMOS technology to achieve ultra-high speed with high
    output drive.
    """

    class Buffer(Module):
        input: F.ElectricLogic
        output: F.ElectricLogic

        @L.rt_field
        def bridge(self):
            return F.can_bridge_defined(self.input, self.output)

        def __preinit__(self):
            pass

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    power: F.ElectricPower
    buffer = L.list_field(2, Buffer)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )
    lcsc_id = L.f_field(F.has_descriptive_properties_defined)({"LCSC": "C7394039"})
    descriptive_properties = L.f_field(F.has_descriptive_properties_defined)(
        {
            DescriptiveProperties.manufacturer: "UMW(Youtai Semiconductor Co., Ltd.)",
            DescriptiveProperties.partno: "SN74LVC2G34DBVR(UMW)",
        }
    )
    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2403221055_UMW-Youtai-Semiconductor-Co---Ltd--SN74LVC2G34DBVR-UMW_C7394039.pdf"
    )

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self, gnd_only=True)
        )

    @L.rt_field
    def attach_via_pinmap(self):
        return F.can_attach_to_footprint_via_pinmap(
            {
                "1": self.buffer[0].input.line,
                "2": self.power.lv,
                "3": self.buffer[1].input.line,
                "4": self.buffer[1].output.line,
                "5": self.power.hv,
                "6": self.buffer[0].output.line,
            }
        )

    def __preinit__(self):
        # ------------------------------------
        #           connections
        # ------------------------------------

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        self.power.voltage.constrain_subset(L.Range(1.65 * P.V, 5.5 * P.V))
