# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.brightness import TypicalLuminousIntensity
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P  # noqa: F401

# Components


logger = logging.getLogger(__name__)


class App(Module):
    """
    Main module of the HyperPD project.
    """

    class USB_Power_Source(Module):
        """
        USB Type-C connector with PD trigger (set to 20V).
        A voltage monitor is enabling a relay to only output
        power when the voltage is 20V.
        """

        usb_pr_trigger: F.WCHJiangsu_Qin_Heng_CH224K_ReferenceDesign
        usb_connector: F.USB_Type_C_Receptacle_16_pin
        relay: F.Relay

        power_out: F.ElectricPower

        def __preinit__(self):
            self.usb_pr_trigger.vbus.connect(self.usb_connector.power)
            self.usb_pr_trigger.cc[0].connect(self.usb_connector.cc1)
            self.usb_pr_trigger.cc[1].connect(self.usb_connector.cc2)
            self.usb_pr_trigger.usb_data.connect(self.usb_connector.d)

            self.relay.switch_a_no.connect(self.power_out.hv)
            self.relay.switch_a_common.connect(self.usb_pr_trigger.vbus.hv)

            self.power_out.lv.connect(self.usb_pr_trigger.vbus.lv)

    class DCDC_Module(Module):
        """
        DCDC module with a 5V output. Conncted via 2 wire terminal blocks to the PCB.
        """

        class Power_Connector(Module):
            """
            Power connector to connect the leads of the DCDC converter.
            """

            power: F.ElectricPower

            designator_prefix = L.f_field(F.has_designator_prefix_defined)(
                F.has_designator_prefix.Prefix.J
            )

            lcsc_id = L.f_field(F.has_descriptive_properties_defined)(
                {"LCSC": "C475222"}
            )

            def __preinit__(self):
                self.add(
                    F.can_attach_to_footprint_via_pinmap(
                        pinmap={
                            "1": self.power.hv,
                            "2": self.power.lv,
                        }
                    )
                )

        class DCDC_Converter(Module):
            """
            DCDC converter monoblock with wire leads.
            """

            power_in: F.ElectricPower
            power_out: F.ElectricPower

            designator_prefix = L.f_field(F.has_designator_prefix_defined)(
                F.has_designator_prefix.Prefix.MOD
            )

            no_pick: F.has_part_removed

            @L.rt_field
            def footprint(self):
                return F.has_footprint_defined(
                    F.KicadFootprint(
                        "custom:DCDC_Module", pin_names=["1", "2", "3", "4"]
                    )
                )

            # @L.rt_field
            # def single_reference(self):
            #    return F.ElectricLogic.connect_all_module_references(self, gnd_only=True)

            def __preinit__(self):
                self.power_out.voltage.constrain_subset(
                    L.Range.from_center_rel(5 * P.V, 0.02)
                )

                self.add(
                    F.can_attach_to_footprint_via_pinmap(
                        pinmap={
                            "1": self.power_in.hv,
                            "2": self.power_in.lv,
                            "3": self.power_out.lv,
                            "4": self.power_out.hv,
                        }
                    )
                )

        power_in_connector: Power_Connector
        power_out_connector: Power_Connector
        dcdc_converter: DCDC_Converter

        power_in: F.ElectricPower
        power_out: F.ElectricPower

        @L.rt_field
        def bridge(self):
            return F.can_bridge_defined(self.power_in, self.power_out)

        def __preinit__(self):
            self.power_in.connect(
                *[self.dcdc_converter.power_in, self.power_in_connector.power]
            )
            self.power_out.connect(
                *[self.dcdc_converter.power_out, self.power_out_connector.power]
            )

    class LED_Connector(Module):
        """
        LED strip connector with power and
        """

        power: F.ElectricPower
        data: F.ElectricLogic
        clock: F.ElectricLogic

        designator_prefix = L.f_field(F.has_designator_prefix_defined)(
            F.has_designator_prefix.Prefix.J
        )

        # @L.rt_field
        # def single_reference(self):
        #    return F.ElectricLogic.connect_all_module_references(self, gnd_only=True)

        lcsc_id = L.f_field(F.has_descriptive_properties_defined)({"LCSC": "C19268030"})

        def __preinit__(self):
            self.add(
                F.can_attach_to_footprint_via_pinmap(
                    pinmap={
                        "1": self.power.hv,
                        "2": self.power.lv,
                        "3": self.data.signal,
                        "4": self.clock.signal,
                    }
                )
            )

    pd_power_supply: USB_Power_Source
    dcdc_module: DCDC_Module
    mcu: F.RaspberryPiPico
    led_connector = L.list_field(2, LED_Connector)

    def __preinit__(self):
        # connections
        self.mcu.base.ldo.power_in.connect(self.pd_power_supply.relay.coil_power)
        self.mcu.base.ldo.power_in.lv.connect(self.dcdc_module.power_in.lv)

        for i, led_con in enumerate(self.led_connector):
            self.pd_power_supply.power_out.connect_via(
                self.dcdc_module, led_con.power
            )  # TODO: connect_via(fuse)

            # swap clock and data with the next connector
            # HyperSerialPico has in SK6812/WS281x mode, data[0] on gpio[2] and data[1] on gpio[3]
            # in SPI LED mode, you use only 1 of the 2 connectors for data and clock
            led_con.clock.connect(self.mcu.base.rp2040.gpio[2 + i])
            led_con.data.connect(self.mcu.base.rp2040.gpio[3 - i])

        # Select specific part numbers
        self.pd_power_supply.usb_pr_trigger.power_good_indicator.led.led.add(
            F.has_explicit_part.by_supplier(
                "C2297",
                pinmap={
                    "1": self.pd_power_supply.usb_pr_trigger.power_good_indicator.led.led.anode,
                    "2": self.pd_power_supply.usb_pr_trigger.power_good_indicator.led.led.cathode,
                },
            )
        )
        self.pd_power_supply.usb_connector.add(
            F.has_explicit_part.by_supplier("C165948")
        )
        self.pd_power_supply.relay.add(
            F.has_explicit_part.by_supplier(
                "C35449",
                pinmap={
                    "1": self.pd_power_supply.relay.coil_power.hv,
                    "2": self.pd_power_supply.relay.switch_a_no,
                    "3": self.pd_power_supply.relay.switch_a_nc,
                    "4": self.pd_power_supply.relay.coil_power.lv,
                    "5": self.pd_power_supply.relay.switch_a_common,
                },
            )
        )

        self.mcu.add(
            F.has_footprint_defined(
                F.KicadFootprint(
                    "ki-lime-pi-pico:RaspberryPi_Pico_Common",
                    pin_names=[],
                )
            )
        )
        self.mcu.add(
            F.can_attach_to_footprint_via_pinmap(
                {
                    **{f"{i+1}": self.mcu.header[0].contact[i] for i in range(20)},
                    **{f"{i+21}": self.mcu.header[1].contact[i] for i in range(20)},
                }
            )
        )
        self.mcu.add(F.has_part_removed())
