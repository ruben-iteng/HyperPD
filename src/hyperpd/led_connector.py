# SPDX-License-Identifier: MIT


import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P  # noqa: F401


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
