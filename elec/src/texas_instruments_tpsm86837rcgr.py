# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto
import logging

from atopile.errors import UserNotImplementedError
from faebryk.core.parameter import IsSubset, Parameter
import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.sets.quantity_sets import Quantity_Interval
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
    class SwitchingFrequency(Enum):
        _800kHz = L.Range.from_center_rel(162 * P.kohm, 0.01)
        _1200kHz = L.Range.from_center_rel(374 * P.kohm, 0.01)

    # @assert_once
    # def set_output_voltage(self, voltage: Quantity_Interval, owner: Module):
    #     """
    #     Set the output voltage of the module
    #     """

    #     # Voltage divider resistors
    #     # TODO: replace with voltage divider
    #     resistor_top = F.Resistor()
    #     resistor_top.resistance.constrain_subset(L.Range(0.0 * P.ohm, 82.0 * P.kohm))
    #     resistor_bottom = F.Resistor()
    #     resistor_bottom.resistance.constrain_subset(
    #         L.Range.from_center_rel(10 * P.kohm, 0.01)
    #     )

    #     # optional resistor to in-circuit measure frequency response of the control loop
    #     resistor_control_loop_measurement = F.Resistor()
    #     resistor_control_loop_measurement.allow_removal_if_zero()
    #     resistor_control_loop_measurement.resistance.constrain_subset(
    #         L.Range.from_center_rel(49.9 * P.ohm, 0.01)
    #     )

    #     # Optional capacitor to improve the load transient response or improve the loop-phase margin
    #     capacitor_filter = F.Capacitor()
    #     # capacitor_filter.allow_removal_if_zero() #TODO: make similar function
    #     capacitor_filter.capacitance.constrain_subset(
    #         L.Range.from_center_rel(10 * P.nF, 0.01)
    #     )

    #     self.feedback.connect_via(resistor_bottom, self.power_analog.lv)
    #     self.feedback.connect_via(
    #         [resistor_top, resistor_control_loop_measurement], self.power_out.hv
    #     )
    #     self.feedback.connect_via(
    #         [capacitor_filter, resistor_control_loop_measurement],
    #         self.power_out.hv,
    #     )

    #     # self.output_voltage.alias_is(voltage)
    #     self.output_voltage.alias_is(
    #         0.6 * (1 + resistor_top.resistance / resistor_bottom.resistance) * P.V
    #     )
    #     owner.add(resistor_top)
    #     owner.add(resistor_bottom)

    @assert_once
    def set_soft_start_time(self, time: float, owner: Module):
        """
        Set the soft start time of the module in ms.
        """
        # capacitor (Css) between soft start and analog ground
        # Tss[ms] = Css*VREF/ISS
        # ISS = 6uA
        # VREF = 0.6V +- 1%

        # 22nF gives 2.2ms

        soft_start_time = L.p_field(
            units=P.ms,
            likely_constrained=True,
            soft_set=L.Range.from_center_rel(time * P.ms, 0.01),
        )

        soft_start_timing_capacitor = F.Capacitor()

        soft_start_charging_current = L.Range.from_center_rel(
            6 * P.uA, 0.01
        )  # TODO: Datasheet does not mention a range
        soft_start_voltage_reference = L.Range.from_center_rel(0.6 * P.V, 0.01)

        soft_start_time.alias_is(
            soft_start_timing_capacitor.capacitance
            * soft_start_voltage_reference
            / soft_start_charging_current
        )

        self.add(soft_start_time)
        owner.add(soft_start_timing_capacitor)

        # connections
        self.soft_start.connect_via(soft_start_timing_capacitor, self.power_analog.lv)

    @assert_once
    def set_input_under_voltage_lockout(
        self,
        voltage_start: float,
        voltage_stop: float,
        owner: Module,
    ):
        """
        Set the input under voltage lockout of the module.
        The module is by default enabled, but the enable pin can also be used to set
        a voltage threshold to enable/disable the module.
        """
        raise UserNotImplementedError("This function is not implemented yet")
        # Ip = 1uA
        # Ih = 3uA
        # VENfalling = 1.07V
        # VENrising = 1.18V
        # VENmax = 5.5V
        # VIN UVLO threshold = 550mV

        # r1=(Vstart*(VENfaling/VENrising)-Vstop)/(Ip*(1-VENfaling/VENrising)+Ih)
        # r2=(r1*VENfaling)/(Vstop-VENfaling+r1*(Ip+Ih))
        # VEN = (r2*VIN+r1*r2*(Ip+Ih))/(r1+r2)

    # @assert_once
    # def set_switching_frequency(self, frequency: SwitchingFrequency, owner: Module):
    #     """
    #     Set the switching frequency of the module.
    #     """
    #     switching_frequency_resistor = F.Resistor()
    #     if frequency == self.SwitchingFrequency._800kHz:
    #         switching_frequency_resistor.resistance.constrain_subset(
    #             L.Range.from_center_rel(162 * P.kohm, 0.01)
    #         )
    #     else:
    #         switching_frequency_resistor.resistance.constrain_subset(
    #             L.Range.from_center_rel(374 * P.kohm, 0.01)
    #         )

    #     self.frequency_mode.connect_via(
    #         switching_frequency_resistor, self.power_analog.lv
    #     )

    #     owner.add(switching_frequency_resistor)

    # ----------------------------------------
    #              interfaces
    # ----------------------------------------
    power_out = L.d_field(lambda: F.ElectricPower().make_source())  # pins: 1, 16
    frequency_mode: F.Electrical  # pin: 2
    enable: F.EnablePin  # pin: 3
    feedback: F.Electrical  # pin: 4
    power_analog: F.ElectricPower  # pin: 5
    power_good: F.ElectricLogic  # pin: 6
    soft_start: F.Electrical  # pin: 7
    power_in: F.ElectricPower  # pins: 8, 9
    # n.c. switchng_node: F.Electrical  # pins: 10, 11
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
        domain=L.Domains.ENUM(SwitchingFrequency),
    )

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
                "3": self.enable.enable.signal,
                "4": self.feedback,
                "5": self.power_analog.lv,
                "6": self.power_good.signal,
                "7": self.soft_start,
                "8": self.power_in.hv,
                "9": self.power_in.hv,
                "10": None,  # self.switching_node,
                "11": None,  # self.switching_node,
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
        # self.enable.make_required()
        self.power_in.voltage.constrain_subset(L.Range(4.5 * P.V, 28 * P.V))
        self.power_out.voltage.constrain_subset(self.output_voltage)

        # The datasheet does not specify a specific voltage, but there is an image of the internal circuitry showing a 5V rail
        self.power_analog.voltage.constrain_subset(
            L.Range.from_center_rel(5 * P.V, 0.01)
        )
