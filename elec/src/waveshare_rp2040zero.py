# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P  # noqa: F401
from faebryk.libs.picker.picker import DescriptiveProperties

logger = logging.getLogger(__name__)


class WaveshareRp2040Zero(Module):
    """
    RP2040-Zero dev board from Waveshare in a 18x23.5mm package
    """

    # ----------------------------------------
    #                modules
    # ----------------------------------------

    # ----------------------------------------
    #              interfaces
    # ----------------------------------------
    gpio = L.list_field(30, F.ElectricLogic)
    # gpio 16 is connected to the onboard WS2812 LED
    # gpio 17-25 are exposed on the bottom solder pads

    power_3v3: F.ElectricPower
    power_5v: F.ElectricPower

    # ----------------------------------------
    #              parameters
    # ----------------------------------------

    # ----------------------------------------
    #                traits
    # ----------------------------------------
    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self, gnd_only=True)
        )

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.MOD
    )
    lcsc_id = L.f_field(F.has_descriptive_properties_defined)({"LCSC": "C5350143"})
    descriptive_properties = L.f_field(F.has_descriptive_properties_defined)(
        {
            DescriptiveProperties.manufacturer: "Waveshare",
            DescriptiveProperties.partno: "RP2040-Zero",
        }
    )
    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://www.waveshare.com/wiki/RP2040-Zero"
    )

    @L.rt_field
    def attach_via_pinmap(self):
        return F.can_attach_to_footprint_via_pinmap(
            {
                "1": self.gpio[0].line,
                "2": self.gpio[1].line,
                "3": self.gpio[2].line,
                "4": self.gpio[3].line,
                "5": self.gpio[4].line,
                "6": self.gpio[5].line,
                "7": self.gpio[6].line,
                "8": self.gpio[7].line,
                "9": self.gpio[8].line,
                "10": self.gpio[9].line,
                "11": self.gpio[10].line,
                "12": self.gpio[11].line,
                "13": self.gpio[12].line,
                "14": self.gpio[13].line,
                "15": self.gpio[14].line,
                "16": self.gpio[15].line,
                "17": self.gpio[26].line,
                "18": self.gpio[27].line,
                "19": self.gpio[28].line,
                "20": self.gpio[29].line,
                "21": self.power_3v3.hv,
                "22": self.power_5v.lv,
                "23": self.power_5v.hv,
            }
        )

    def __preinit__(self):
        # ------------------------------------
        #           connections
        # ------------------------------------

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        self.power_3v3.voltage.constrain_subset(
            L.Range.from_center_rel(3.3 * P.V, 0.01)
        )
        self.power_5v.voltage.constrain_subset(L.Range.from_center_rel(5 * P.V, 0.01))
