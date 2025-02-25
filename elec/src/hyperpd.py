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
from .digital_led_buffer import DigitalLEDBuffer

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
            fused_power = self.power.fused()
            fuse = fused_power.get_first_child_of_type(F.Fuse)
            fuse.trip_current.constrain_subset(
                L.Range.from_center_rel(8 * P.A, 10 * P.percent)
            )
            fuse.fuse_type.alias_is(F.Fuse.FuseType.RESETTABLE)
            self.add(
                F.can_attach_to_footprint_via_pinmap(
                    pinmap={
                        "1": fused_power.hv,
                        "2": fused_power.lv,
                        "3": self.data.line,
                        "4": self.clock.line,
                    }
                )
            )

    pd_power_supply: USB_Power_Source
    dcdc_module: TexasInstrumentsTPSM86837RCGR_ReferenceDesign
    mcu: F.RaspberryPiPico
    led_connector = L.list_field(2, LED_Connector)
    led_buffer: DigitalLEDBuffer

    def __preinit__(self):
        # ------------------------------------
        #            aliases
        # ------------------------------------
        vbus = self.pd_power_supply.power_out

        # ------------------------------------
        #              connections
        # ------------------------------------
        # power
        # self.mcu.base.ldo.power_in.lv.connect(self.dcdc_module.power_in.lv)
        # self.led_buffer.power.connect(self.dcdc_module.power_out)

        # data - mcu > buffer
        # adafruit scorpio board is using the following gpio for the led strip:
        for i in range(16, 24):
            self.mcu.base.rp2040.gpio[i].connect(self.led_buffer.input_channel[i - 16])

        # data - buffer > led
        for i, led_con in enumerate(self.led_connector):
            vbus.connect_via(self.dcdc_module, led_con.power)

            # swap clock and data with the next connector
            # HyperSerialPico has in SK6812/WS281x mode:
            # TODO: support hardware switch to change between SK6812/WS281x and SPI LED mode
            #   segment 0
            #       on gpio 16
            #       buffer channel 0
            #       output connector 0
            #   segment 1
            #       on gpio 17
            #       buffer channel 1
            #       output connector 1
            # in SPI LED mode both connector are using the same gpio
            #   clock
            #       on gpio 18
            #       buffer channel 2
            #   data
            #       on gpio 19
            #       buffer channel 3
            led_con.clock.connect(self.led_buffer.led_channel[2])
            led_con.data.connect(self.led_buffer.led_channel[3])

        # ------------------------------------
        #              Net names
        # ------------------------------------
        nets = {
            "vbus": vbus.hv,
            "data": self.led_connector[0].data.line,
            "clock": self.led_connector[0].clock.line,
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
        # self.dcdc_module.power_module.switching_frequency.constrain_subset(800 * P.kHz)
        self.dcdc_module.power_out.voltage.constrain_subset(
            L.Range(5.0 * P.V, 5.1 * P.V)
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
