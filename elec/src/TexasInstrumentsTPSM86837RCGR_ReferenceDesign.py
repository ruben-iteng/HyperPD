# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.parameter import Add, Multiply
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
        """
        Feedback resistor divider to measure the output voltage with filtering and
        control loop measurement
        """

        class ResistorControlLoopMeasurement(Module):
            """Resistor to in-circuit measure frequency response of the control loop"""

            power_in: F.ElectricPower
            power_out: F.ElectricPower

            resistor: F.Resistor
            testpoint = L.list_field(2, F.TestPoint)

            @L.rt_field
            def can_bridge(self):
                return F.can_bridge_defined(self.power_in, self.power_out)

            def __preinit__(self):
                self.power_in.hv.connect_via(
                    [
                        self.testpoint[0].contact,
                        self.resistor,
                        self.testpoint[1].contact,
                    ],
                    self.power_out.hv,
                )
                self.power_in.lv.connect(self.power_out.lv)

                self.resistor.resistance.constrain_subset(
                    L.Range.from_center_rel(49.9 * P.ohm, 0.01)
                )

                self.power_in.voltage.alias_is(
                    self.power_out.voltage
                    + (self.power_out.max_current * self.resistor.resistance)
                )
                self.power_out.voltage.alias_is(
                    self.power_in.voltage
                    - (self.power_out.max_current * self.resistor.resistance)
                )

                self.power_out.max_current.constrain_superset(
                    L.Range.from_center_rel(1 * P.mA, 0.01)
                )

        # ----------------------------------------
        #              interfaces
        # ----------------------------------------
        feedback: F.ElectricSignal
        output_power_rail: F.ElectricPower

        # ----------------------------------------
        #               parameters
        # ----------------------------------------
        output_voltage = L.p_field(units=P.V)

        # ----------------------------------------
        #               modules
        # ----------------------------------------
        resistor_divider: F.ResistorVoltageDivider

        resistor_control_loop_measurement: ResistorControlLoopMeasurement

        # capacitor to improve the load transient response or improve the loop-phase margin
        load_transient_filter_capacitor: F.Capacitor

        nettie = L.f_field(F.NetTie)(
            width=0.5,
            pin_count=2,
            pad_type=F.NetTie.PadType.SMD,
            connect_gnd=True,
        )

        def __preinit__(self):
            # ------------------------------------
            #           connections
            # ------------------------------------
            self.output_power_rail.connect_via(
                [self.nettie, self.resistor_control_loop_measurement],
                self.resistor_divider.power,
            )
            self.resistor_divider.output.connect(self.feedback)
            # TODO: ---------------
            self.resistor_divider.power.lv.connect(self.feedback.reference.lv)
            self.feedback.line.connect(
                self.feedback.reference.hv
            )  # TODO: is this needed?
            # ---------------------
            self.feedback.line.connect_via(
                self.load_transient_filter_capacitor, self.resistor_divider.power.hv
            )

            # ------------------------------------
            #          parametrization
            # ------------------------------------
            # TODO: This should not need key words
            self.output_voltage.alias_is(
                Multiply(0.6 * P.V, Add(1, self.resistor_divider.ratio))
            )

            # Valid values from the datasheet
            self.resistor_divider.r_top.resistance.constrain_subset(
                L.Range(0.0 * P.ohm, 82.0 * P.kohm)
            )
            self.resistor_divider.r_bottom.resistance.constrain_subset(
                L.Range.from_center_rel(10 * P.kohm, 0.01)
            )
            self.load_transient_filter_capacitor.capacitance.constrain_subset(
                L.Range.from_center_rel(47 * P.pF, 0.01)
            )

            # use 0402 packages for all capacitors and resistors that do not
            # have a footprint defined yet
            for comp in self.get_children_modules(
                types=(F.Capacitor, F.Resistor),
                f_filter=lambda m: not m.has_trait(F.has_footprint),
            ):
                comp.add(
                    F.has_package(
                        F.has_package.Package.C0402
                        if isinstance(comp, F.Capacitor)
                        else F.has_package.Package.R0402
                    )
                )

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

        # connect the output voltage feedback resistor-divider
        self.output_voltage_feedback.output_power_rail.connect(
            self.power_module.power_out
        )
        self.output_voltage_feedback.feedback.connect(self.power_module.feedback)
        self.power_module.power_analog.connect(self.power_module.feedback.reference)

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        self.output_voltage_feedback.resistor_divider.max_current.alias_is(
            self.power_module.feedback.reference.max_current
        )
        self.power_out.voltage.constrain_subset(
            L.Range.from_center_rel(5 * P.V, 5 * P.percent)
        )
        # self.power_module.output_voltage.alias_is(
        #    self.output_voltage_feedback.output_voltage
        # )

        # soft start -------------------------
        # capacitor (Css) between soft start and analog ground
        # Tss[ms] = Css*VREF/ISS
        # ISS = 6uA
        # VREF = 0.6V +- 1%
        # 22nF gives 2.2ms
        soft_start_charging_current = (
            L.Single(6 * P.uA)  # no range in datasheet
            # L.Range.from_center_rel(6 * P.uA, 0.01)
        )
        soft_start_voltage_reference = L.Range.from_center_rel(0.6 * P.V, 0.01)

        self.power_module.soft_start_time.alias_is(
            self.soft_start_timing_capacitor.capacitance
            * soft_start_voltage_reference
            / soft_start_charging_current
        )
        self.soft_start_timing_capacitor.capacitance.alias_is(
            (soft_start_charging_current * self.power_module.soft_start_time)
            / soft_start_voltage_reference
        )
        # self.soft_start_timing_capacitor.capacitance.constrain_subset(
        #    L.Range.from_center_rel(22 * P.nF, 0.01)
        # )  # TODO: remove, makes picking extremely slow if removed
        # self.power_module.soft_start_time.constrain_subset(
        #    L.Range.from_center_rel(2.2 * P.ms, 0.1)
        # )
        self.soft_start_timing_capacitor.add(
            F.is_pickable_by_supplier_id(supplier_part_id="C77023")
        )
        # switching frequency ----------------
        # map switching frequency to config resistor value
        self.power_module.switching_frequency.constrain_mapping(
            self.switching_frequency_resistor.resistance,
            {
                800 * P.kHz: L.Range.from_center_rel(162 * P.kohm, 0.01),
                1200 * P.kHz: L.Range.from_center_rel(374 * P.kohm, 0.01),
            },
        )
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
        # use 0402 packages for all capacitors and resistors that do not
        # have a footprint defined yet
        # for comp in self.get_children_modules(
        #     types=(F.Capacitor, F.Resistor),
        #     f_filter=lambda m: not m.has_trait(F.has_footprint),
        # ):
        #     comp.add(
        #         F.has_package(
        #             F.has_package.Package.C0402
        #             if isinstance(comp, F.Capacitor)
        #             else F.has_package.Package.R0402
        #         )
        #     )
