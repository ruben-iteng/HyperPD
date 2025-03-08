# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.exporters.pcb.layout.next_to_pin import LayoutNextToPin
import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P  # noqa: F401
from .SN74LVC2G34 import SN74LVC2G34

logger = logging.getLogger(__name__)


class DigitalLEDBuffer(Module):
    """
    2 channel buffer/level shifter for digital LEDs (like neopixels)
    """

    # ----------------------------------------
    #                modules
    # ----------------------------------------
    buffer_ic: SN74LVC2G34
    current_limit_resistors = L.list_field(2, F.Resistor)

    # ----------------------------------------
    #              interfaces
    # ----------------------------------------
    power: F.ElectricPower
    input_channel = L.list_field(2, F.ElectricLogic)
    led_channel = L.list_field(2, F.ElectricLogic)

    # ----------------------------------------
    #              parameters
    # ----------------------------------------

    # ----------------------------------------
    #                traits
    # ----------------------------------------
    # @L.rt_field
    # def bridge(self):
    #    return F.can_bridge_defined(self.input_channel, self.led_channel)

    def __preinit__(self):
        # ------------------------------------
        #           connections
        # ------------------------------------
        for i, (input, led_chan) in enumerate(
            zip(self.input_channel, self.led_channel)
        ):
            input.connect(self.buffer_ic.buffer[i].input)
            led_chan.line.connect_via(
                self.current_limit_resistors[i], self.buffer_ic.buffer[i].output.line
            )

        self.buffer_ic.power.connect(self.power)
        decoupling_cap = self.power.decoupled.decouple(owner=self).capacitors[0]

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        self.power.voltage.constrain_subset(L.Range(min=2.0 * P.V, max=5.5 * P.V))

        for i, res in enumerate(self.current_limit_resistors):
            res.resistance.constrain_subset(L.Range.from_center_rel(470 * P.ohm, 0.01))
            res.add(F.has_package(F.has_package.Package.R0402))
            res.add(
                F.has_pcb_layout_defined(
                    layout=LayoutNextToPin(
                        interface=self.buffer_ic.buffer[i].output.line,
                        distance_between_pad_edges=0.5 if not i % 2 else 2.75,
                    )
                )
            )

        decoupling_cap.add(F.has_package(F.has_package.Package.C0402))
        decoupling_cap.capacitance.constrain_subset(
            L.Range.from_center_rel(0.1 * P.uF, 0.1)
        )
        decoupling_cap.add(
            F.has_pcb_layout_defined(
                layout=LayoutNextToPin(
                    interface=self.buffer_ic.power.hv, distance_between_pad_edges=0.5
                )
            )
        )
