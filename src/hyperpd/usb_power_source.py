import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P  # noqa: F401

logger = logging.getLogger(__name__)


class USB_Power_Source(Module):
    """
    USB Type-C connector with PD trigger (set to 20V).
    A voltage monitor is enabling a relay to only output
    power when the voltage is 20V.
    """

    usb_pr_trigger: F.WCHJiangsu_Qin_Heng_CH224K_ReferenceDesign
    usb_connector: F.USB_Type_C_Receptacle_16_pin

    power_out: F.ElectricPower
    power_good: F.ElectricLogic  # TODO: active low

    def __preinit__(self):
        self.usb_pr_trigger.vbus.connect(self.usb_connector.power)
        self.usb_pr_trigger.cc[0].connect(self.usb_connector.cc1)
        self.usb_pr_trigger.cc[1].connect(self.usb_connector.cc2)
        self.usb_pr_trigger.usb_data.connect(self.usb_connector.d)

        self.power_out.connect(self.usb_pr_trigger.vbus)  # TODO: fused
        self.power_good.connect(self.usb_pr_trigger.controller.power_good)

        # Select specific part numbers
        self.usb_pr_trigger.power_good_indicator.led.led.add(
            F.has_explicit_part.by_supplier(
                "C72038",
                pinmap={
                    "2": self.usb_pr_trigger.power_good_indicator.led.led.anode,
                    "1": self.usb_pr_trigger.power_good_indicator.led.led.cathode,
                },
            )
        )
        self.usb_connector.add(F.has_explicit_part.by_supplier("C165948"))
