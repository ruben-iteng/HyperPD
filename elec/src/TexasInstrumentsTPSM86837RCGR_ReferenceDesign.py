# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.parameter import Add, Divide, Multiply
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
        feedback: F.ElectricSignal
        output_power_rail: F.ElectricPower
        analog_power_rail: F.ElectricPower

        # ----------------------------------------
        #               parameters
        # ----------------------------------------
        output_voltage = L.p_field(units=P.V)

        # ----------------------------------------
        #               modules
        # ----------------------------------------
        resistor_divider: F.ResistorVoltageDivider

        # Optional resistor to in-circuit measure frequency response of the control loop
        resistor_control_loop_measurement: F.Resistor
        # TODO: connect the 2 testpoints to the feedback resistor
        # frequency_response_testpoints: L.list_field(2, F.Testpoints)

        # capacitor to improve the load transient response or improve the loop-phase margin
        capacitor_filter: F.Capacitor

        # nettie: F.NetTie

        def __preinit__(self):
            # ------------------------------------
            #           connections
            # ------------------------------------
            self.output_power_rail.hv.connect_via(
                [
                    self.resistor_control_loop_measurement,
                    self.resistor_divider.resistor[0],  # TODO very ugly
                ],
                self.feedback.line,
            )
            self.feedback.reference.connect(
                self.resistor_divider.power_out
            )  # TODO: is this needed?

            self.feedback.line.connect_via(
                self.capacitor_filter, self.resistor_divider.power_in.hv
            )  # TODO very ugly

            # connect analog and high power rails via a single point (net tie)
            # self.output_power_rail.connect_via(
            #    self.nettie,
            #    self.analog_power_rail,
            # )

            # ------------------------------------
            #          parametrization
            # ------------------------------------
            # TODO: This should not need key words
            self.output_voltage.alias_is(
                Multiply(0.6 * P.V, Add(1, self.resistor_divider.ratio))
            )

            # Valid values from the datasheet
            # self.resistor_divider.resistor[0].resistance = L.p_field(
            #    units=P.ohm,
            #    within=L.Range(0.0 * P.ohm, 82.0 * P.kohm),
            # )
            self.resistor_divider.resistor[1].resistance.constrain_subset(
                L.Range.from_center_rel(10 * P.kohm, 0.01)
            )
            self.resistor_control_loop_measurement.resistance.constrain_subset(
                L.Range.from_center_rel(49.9 * P.ohm, 0.01)
            )
            self.capacitor_filter.capacitance.constrain_subset(
                L.Range.from_center_rel(47 * P.pF, 0.01)
            )

            # use 0402 packages for all capacitors and resistors that do not
            # have a footprint defined yet
            for cap in self.get_children_modules(
                types=F.Capacitor,
                f_filter=lambda m: not m.has_trait(F.has_footprint),
            ):
                cap.add(F.has_package(F.has_package.Package.C0402))
            for res in self.get_children_modules(
                types=F.Resistor,
                f_filter=lambda m: not m.has_trait(F.has_footprint),
            ):
                res.add(F.has_package(F.has_package.Package.R0402))

    # ----------------------------------------
    #               modules
    # ----------------------------------------
    power_module: TEXAS_INSTRUMENTS_TPSM86837RCGR
    switching_frequency_resistor: F.Resistor
    soft_start_timing_capacitor: F.Capacitor
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
            self.switching_frequency_resistor, self.power_module.power_analog.lv
        )

        self.power_module.soft_start.connect_via(
            self.soft_start_timing_capacitor, self.power_module.power_analog.lv
        )

        # connect the output voltage feedback resistor devider
        self.output_voltage_feedback.output_power_rail.connect(
            self.power_module.power_out
        )
        self.output_voltage_feedback.analog_power_rail.connect(
            self.power_module.power_analog
        )
        self.output_voltage_feedback.feedback.connect(self.power_module.feedback)

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        self.power_module.output_voltage.alias_is(
            self.output_voltage_feedback.output_voltage
        )

        # soft start
        soft_start_charging_current = (
            # L.Single(6 * P.uA)  # no range in datasheet
            L.Range.from_center_rel(6 * P.uA, 0.01)
        )
        soft_start_voltage_reference = L.Range.from_center_rel(0.6 * P.V, 0.01)

        self.power_module.soft_start_time.alias_is(
            (
                self.soft_start_timing_capacitor.capacitance
                * soft_start_voltage_reference
                / soft_start_charging_current
            )
            * P.F
        )
        self.soft_start_timing_capacitor.capacitance.alias_is(
            (soft_start_charging_current / soft_start_voltage_reference)
            / self.power_module.soft_start_time
        )
        # self.soft_start_timing_capacitor.capacitance.constrain_subset(
        #    L.Range.from_center_rel(22 * P.nF, 0.01)
        # )  # TODO: remove
        self.power_module.soft_start_time.constrain_subset(
            L.Range.from_center_rel(2.2 * P.ms, 0.1)
        )

        # map switching frequency to config resistor value
        self.power_module.switching_frequency.constrain_mapping(
            self.switching_frequency_resistor.resistance,
            {
                800 * P.kHz: L.Range.from_center_rel(162 * P.kohm, 0.01),
                1200 * P.kHz: L.Range.from_center_rel(374 * P.kohm, 0.01),
            },
        )
        # TODO: remove
        self.power_module.switching_frequency.constrain_subset(1200 * P.kHz)
        # TODO: self.enable.make_required()

        # use the recommended in and output capacitors from the offical reference design
        for cap in self.power_in.decoupled.decouple(owner=self, count=2).capacitors:
            cap.capacitance.constrain_subset(L.Range.from_center_rel(10 * P.uF, 0.1))
            cap.add(
                F.has_descriptive_properties_defined(
                    {
                        DescriptiveProperties.manufacturer: "Murata Electronics",
                        DescriptiveProperties.partno: "GRM32ER7YA106KA12L",
                    }
                )
            )
        for cap in self.power_out.decoupled.decouple(owner=self, count=3).capacitors:
            cap.add(
                F.has_descriptive_properties_defined(
                    {
                        DescriptiveProperties.manufacturer: "Murata Electronics",
                        DescriptiveProperties.partno: "GRM32ER71E226KE15L",
                    }
                )
            )
