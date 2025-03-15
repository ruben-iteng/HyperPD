# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from atopile.errors import UserNotImplementedError
import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P  # noqa: F401
from faebryk.libs.picker.picker import DescriptiveProperties
from faebryk.libs.util import assert_once

logger = logging.getLogger(__name__)


class TEXAS_INSTRUMENTS_TPSM86837RCGR(Module):
    """
    Power Management Modules 4.5V to 28V input voltage, 8A ECO mode,
    synchronous buck module with QFN package
    """

    # ----------------------------------------
    #               modules
    # ----------------------------------------

    # ----------------------------------------
    #              interfaces
    # ----------------------------------------
    power_out = L.d_field(lambda: F.ElectricPower().make_source())  # pins: 1, 16
    frequency_mode: F.Electrical  # pin: 2
    enable: F.EnablePin  # pin: 3
    feedback: F.ElectricSignal  # pin: 4
    power_analog: F.ElectricPower  # pin: 5
    power_good: F.ElectricLogic  # pin: 6
    soft_start: F.Electrical  # pin: 7
    power_in: F.ElectricPower  # pins: 8, 9
    switching_node: F.Electrical  # pins: 10, 11
    """
    Do not connect, only for better thermal dissipation and reduced parasitic impedance.
    """
    # n.c. bootstrap: F.Electrical  # pin: 12
    # power_ground: F.Electrical  # pins: 17, 18, 19

    # ----------------------------------------
    #               parameters
    # ----------------------------------------
    output_voltage = L.p_field(
        units=P.V,
        likely_constrained=True,
        soft_set=L.Range(0.6 * P.V, 5.5 * P.V),
    )
    switching_frequency = L.p_field(
        units=P.kHz,
        likely_constrained=True,
        soft_set=L.DiscreteSet(800 * P.kHz, 1200 * P.kHz),
    )
    soft_start_time = L.p_field(
        units=P.ms,
        likely_constrained=True,
        soft_set=L.Range(0 * P.ms, 1000 * P.ms),
    )
    # under_voltage_lockout = L.p_field(units=P.V)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )
    descriptive_properties = L.f_field(F.has_descriptive_properties_defined)(
        {
            DescriptiveProperties.manufacturer: "TEXAS INSTRUMENTS",
            DescriptiveProperties.partno: "TPSM86837RCGR",
        }
    )
    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://www.ti.com/lit/ds/symlink/tpsm86838.pdf"
    )

    @L.rt_field
    def bridge(self):
        return F.can_bridge_defined(self.power_in, self.power_out)

    # TODO: fix, don't connect analog power to ground
    # @L.rt_field
    # def single_electric_reference(self):
    #    return F.has_single_electric_reference_defined(
    #        F.ElectricLogic.connect_all_module_references(self, exclude=self.analog_power,gnd_only=True)
    #    )

    @L.rt_field
    def attach_via_pinmap(self):
        return F.can_attach_to_footprint_via_pinmap(
            {
                "1": self.power_out.hv,
                "2": self.frequency_mode,
                "3": self.enable.enable.line,
                "4": self.feedback.line,
                "5": self.power_analog.lv,
                "6": self.power_good.line,
                "7": self.soft_start,
                "8": self.power_in.hv,
                "9": self.power_in.hv,
                "10": self.switching_node,
                "11": self.switching_node,
                "12": None,  # self.bootstrap,
                "13": self.power_in.lv,
                "14": self.power_in.lv,
                "15": self.power_in.lv,
                "16": self.power_out.hv,
                "17": self.power_in.lv,
                "18": self.power_in.lv,
                "19": self.power_in.lv,
            }
        )

    def __preinit__(self):
        # ------------------------------------
        #           connections
        # ------------------------------------

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        self.power_in.voltage.constrain_subset(L.Range(4.5 * P.V, 28 * P.V))
        self.power_out.voltage.constrain_subset(self.output_voltage)

        # TODO: sofset is currently not used so constrain manually
        self.power_out.voltage.constrain_subset(L.Range(0.6 * P.V, 5.5 * P.V))
        self.switching_frequency.constrain_subset(
            L.DiscreteSet(800 * P.kHz, 1200 * P.kHz)
        )
        self.soft_start_time.constrain_subset(L.Range(0 * P.ms, 1000 * P.ms))

        # The datasheet does not specify a specific voltage, but there is an image of
        # the internal circuitry showing a 5V rail
        # self.power_analog.voltage.constrain_subset(
        #    L.Range.from_center_rel(5 * P.V, 10 * P.percent)
        # ) TODO: unsolvable ...

        # The datasheet does not specify a specific current, 60uA is calculated from
        # the recommended component values in the datasheet (Table 7-2)
        self.feedback.reference.max_current.constrain_subset(
            L.Range.from_center_rel(60 * P.uA, 10 * P.percent)
        )

        # TODO: no support for high/low/hysteresis/min/max voltage for ElectricLogic
        # self.enable.has_single_electric_reference.reference.voltage.constrain_subset(
        #    L.Range(0.5 * P.V, 5.5 * P.V)
        # )
