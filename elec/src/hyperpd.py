# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P  # noqa: F401

# Components
from .TexasInstrumentsTPSM86837RCGR_ReferenceDesign import (
    TexasInstrumentsTPSM86837RCGR_ReferenceDesign,
)
from .usb_power_source import USB_Power_Source
from .digital_led_buffer import DigitalLEDBuffer
from .waveshare_rp2040zero import WaveshareRp2040Zero
from .led_connector import LED_Connector

logger = logging.getLogger(__name__)


class App(Module):
    """
    Main module of the HyperPD project.
    """

    pd_power_supply: USB_Power_Source
    dcdc_module: TexasInstrumentsTPSM86837RCGR_ReferenceDesign
    mcu: WaveshareRp2040Zero
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
        self.mcu.power_5v.lv.connect(self.dcdc_module.power_in.lv)
        self.led_buffer.power.connect(self.dcdc_module.power_out)

        # data - mcu > buffer
        self.mcu.gpio[2].connect(self.led_buffer.input_channel[1])  # CLK / DATA(WS2812)
        self.mcu.gpio[3].connect(self.led_buffer.input_channel[0])  # DATA

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
            led_con.clock.connect(self.led_buffer.led_channel[1])
            led_con.data.connect(self.led_buffer.led_channel[0])

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
        self.dcdc_module.power_module.switching_frequency.constrain_subset(800 * P.kHz)
        self.dcdc_module.power_out.voltage.constrain_subset(
            L.Range(5.0 * P.V, 5.1 * P.V)
        )
        # self.dcdc_module.power_module.set_soft_start_time(time=2.2, owner=self)
