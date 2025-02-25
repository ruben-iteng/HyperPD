# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P  # noqa: F401
from faebryk.libs.picker.picker import DescriptiveProperties

logger = logging.getLogger(__name__)


class Nexperia_74AHCT245PW(Module):
    """
    Octal bus transceiver; 3-state. 8mA 8 4.5V~5.5V TSSOP-20
    """

    # ----------------------------------------
    #                modules
    # ----------------------------------------

    # ----------------------------------------
    #              interfaces
    # ----------------------------------------
    power: F.ElectricPower
    direction: F.ElectricLogic
    enable: F.ElectricLogic
    data_a = L.list_field(8, F.ElectricLogic)
    data_b = L.list_field(8, F.ElectricLogic)

    # ----------------------------------------
    #              parameters
    # ----------------------------------------

    # ----------------------------------------
    #                traits
    # ----------------------------------------
    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )
    lcsc_id = L.f_field(F.has_descriptive_properties_defined)({"LCSC": "C173388"})
    descriptive_properties = L.f_field(F.has_descriptive_properties_defined)(
        {
            DescriptiveProperties.manufacturer: "Nexperia",
            DescriptiveProperties.partno: "74AHCT245PW,118",
        }
    )
    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://www.lcsc.com/datasheet/lcsc_datasheet_2407241026_Nexperia-74AHCT245PW-118_C173388.pdf"
    )

    # TODO: this should be more dynamic, high/low levels are dependent on power.voltage,
    # but all inputs are power.voltage[max] tolerant
    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    @L.rt_field
    def attach_via_pinmap(self):
        return F.can_attach_to_footprint_via_pinmap(
            {
                "1": self.direction.line,
                "2": self.data_a[0].line,
                "3": self.data_a[1].line,
                "4": self.data_a[2].line,
                "5": self.data_a[3].line,
                "6": self.data_a[4].line,
                "7": self.data_a[5].line,
                "8": self.data_a[6].line,
                "9": self.data_a[7].line,
                "10": self.power.lv,
                "11": self.data_b[7].line,
                "12": self.data_b[6].line,
                "13": self.data_b[5].line,
                "14": self.data_b[4].line,
                "15": self.data_b[3].line,
                "16": self.data_b[2].line,
                "17": self.data_b[1].line,
                "18": self.data_b[0].line,
                "19": self.enable.line,
                "20": self.power.hv,
            }
        )

    def __preinit__(self):
        # ------------------------------------
        #           connections
        # ------------------------------------

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        self.power.voltage.constrain_subset(L.Range(min=2.0 * P.V, max=5.5 * P.V))
