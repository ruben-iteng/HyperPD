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

    class OutputVoltageFeedback(Module):
        # ----------------------------------------
        #              interfaces
        # ----------------------------------------
        feedback: F.Electrical
        output_power_rail: F.ElectricPower
        analog_power_rail: F.ElectricPower

        # ----------------------------------------
        #               parameters
        # ----------------------------------------
        output_voltage = L.p_field(units=P.V)

        # ----------------------------------------
        #               modules
        # ----------------------------------------
        resistor_top: F.Resistor
        resistor_bottom: F.Resistor

        # TODO: make optional?
        # Optional resistor to in-circuit measure frequency response of the control loop
        resistor_control_loop_measurement: F.Resistor

        # TODO: make optional?
        # Optional capacitor to improve the load transient response or improve the loop-phase margin
        capacitor_filter: F.Capacitor

        def __preinit__(self):
            # ------------------------------------
            #           connections
            # ------------------------------------
            self.feedback.connect_via(self.resistor_bottom, self.analog_power_rail.lv)
            self.feedback.connect_via(
                [self.resistor_top, self.resistor_control_loop_measurement],
                self.output_power_rail.hv,
            )
            self.feedback.connect_via(
                [self.capacitor_filter, self.resistor_control_loop_measurement],
                self.output_power_rail.hv,
            )

            # ------------------------------------
            #          parametrization
            # ------------------------------------
            self.output_voltage.alias_is(
                0.6
                * (1 + self.resistor_top.resistance / self.resistor_bottom.resistance)
            )

            # Valid values from the datasheet
            self.resistor_top.resistance.constrain_subset(
                L.Range(0.0 * P.ohm, 82.0 * P.kohm)
            )
            self.resistor_bottom.resistance.constrain_subset(
                L.Range.from_center_rel(10 * P.kohm, 0.01)
            )
            self.resistor_control_loop_measurement.allow_removal_if_zero()
            self.resistor_control_loop_measurement.resistance.constrain_subset(
                L.Range.from_center_rel(49.9 * P.ohm, 0.01)
            )
            # self.capacitor_filter.allow_removal_if_zero() #TODO: make similar function
            self.capacitor_filter.capacitance.constrain_subset(
                L.Range.from_center_rel(10 * P.nF, 0.01)
            )

    # ----------------------------------------
    #               modules
    # ----------------------------------------
    power_module: TEXAS_INSTRUMENTS_TPSM86837RCGR
    switching_frequency_resistor: F.Resistor
    output_voltage_feedback: OutputVoltageFeedback

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

        self.power_module.frequency_mode.connect_via(
            self.switching_frequency_resistor, self.power_in.lv
        )

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        self.power_module.output_voltage.alias_is(
            self.output_voltage_feedback.output_voltage
        )

        self.switching_frequency_resistor.resistance.constrain_subset(
            L.Range.from_center_rel(162 * P.kohm, 0.01)
        )

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

        for res in self.get_children_modules(types=F.Resistor):
            res.add(F.has_package(F.has_package.Package.R0402))
