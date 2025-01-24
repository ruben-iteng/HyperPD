# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.brightness import TypicalLuminousIntensity
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P  # noqa: F401

# Components
from .TexasInstrumentsTPSM86837RCGR_ReferenceDesign import (
    TexasInstrumentsTPSM86837RCGR_ReferenceDesign,
)
from .usb_power_source import USB_Power_Source

logger = logging.getLogger(__name__)


class App(Module):
    """
    Main module of the HyperPD project.
    """

    class LED_Connector(Module):
        """
        LED strip connector with power and data/clock.
        """

        power: F.ElectricPower
        data: F.ElectricLogic
        clock: F.ElectricLogic

        designator_prefix = L.f_field(F.has_designator_prefix)(
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
    dcdc_module: TexasInstrumentsTPSM86837RCGR_ReferenceDesign
    mcu: F.RaspberryPiPico
    led_connector = L.list_field(2, LED_Connector)

    def __preinit__(self):
        # ------------------------------------
        #            aliases
        # ------------------------------------
        vbus = self.pd_power_supply.power_out

        # ------------------------------------
        #              connections
        # ------------------------------------
        # self.mcu.base.ldo.power_in.lv.connect(self.dcdc_module.power_in.lv)

        for i, led_con in enumerate(self.led_connector):
            vbus.connect_via(self.dcdc_module, led_con.power)  # TODO: connect_via(fuse)

            # swap clock and data with the next connector
            # HyperSerialPico has in SK6812/WS281x mode, data[0] on gpio[2] and data[1] on gpio[3]
            # in SPI LED mode, you use only 1 of the 2 connectors for data and clock
            led_con.clock.connect(self.mcu.base.rp2040.gpio[2 + i])
            led_con.data.connect(self.mcu.base.rp2040.gpio[3 - i])

        # ------------------------------------
        #              Net names
        # ------------------------------------
        nets = {
            "vbus": vbus.hv,
            "data": self.led_connector[0].data.signal,
            "clock": self.led_connector[0].clock.signal,
        }
        for name, mif in nets.items():
            assert isinstance(
                mif, F.Electrical
            ), f"You are trying to give a non-electrical interface: {mif}, a net name: {name}"  # noqa E501
            net = F.Net()
            net.add(F.has_overriden_name_defined(name))
            net.part_of.connect(mif)

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        self.dcdc_module.power_module.set_switching_frequency(
            self.dcdc_module.power_module.SwitchingFrequency._800kHz, owner=self
        )
        # self.dcdc_module.power_module.set_output_voltage(
        # voltage=L.Range.from_center_rel(5.0 * P.V, 0.01), owner=self
        # )
        self.dcdc_module.power_module.power_out.voltage.constrain_subset(
            L.Range.from_center_rel(5.0 * P.V, 0.01)
        )
        # self.dcdc_module.power_module.set_soft_start_time(time=2.2, owner=self)

        # TODO this is not nice
        fp = F.KicadFootprint(pin_names=[f"{i+1}" for i in range(40)])
        fp.add(
            F.KicadFootprint.has_kicad_identifier(
                "ki-lime-pi-pico:RaspberryPi_Pico_Common_THT"
            )
        )
        self.mcu.add(
            F.can_attach_to_footprint_via_pinmap(
                {
                    **{f"{i+1}": self.mcu.header[0].contact[i] for i in range(20)},
                    **{f"{i+21}": self.mcu.header[1].contact[i] for i in range(20)},
                }
            )
        ).attach(fp)

        self.mcu.add(F.has_part_removed())
