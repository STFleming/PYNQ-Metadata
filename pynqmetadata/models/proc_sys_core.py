# Copyright (C) 2022 Xilinx, Inc
# SPDX-License-Identifier: BSD-3-Clause

from dataclasses import dataclass, field
from typing import Dict, List

from ..errors import ParameterNotFound, UnexpectedMetadataObjectType
from .core import Core
from .subordinate_port import SubordinatePort
from .signal import Signal

@dataclass(repr=False)
class ProcSysCore(Core):
    """
    A hardened processing system core type
    """

    type: str = "core-procsys"
    ps_name: str = "unknown"
    gpio_name: str = "unknown"
    irq: Dict[str, object] = field(
        default_factory=lambda: (
            {
                "unknown_pin": ((0, 0), (0, 0)),
            }
        )
    )

    @property
    def gpio(self) -> Dict[str, object]:
        """Filters through the ports and signals to generate a gpio_dict"""
        if not hasattr(self, "gpio_name"):
            raise ParameterNotFound(
                f"Trying to find GPIO pins for {self.ref} but cannot determine gpio port"
            )
        else:
            ret = {}
            if self.gpio_name in self.ports:
                gpio_port = self.ports[self.gpio_name]
                for sig in gpio_port.signals.values():
                    for con in sig._connections.values():
                        con_core = con.parent().parent()
                        if isinstance(con_core, Core):
                            ret[con_core.name] = {}
                            ret[con_core.name]["state"] = None
                            ret[con_core.name]["pins"]: List[Signal] = []
                            if "Dout" in con_core.ports:
                                pinlist: List[Signal] = []
                                pin1 = con_core.ports["Dout"].signals["Dout"]
                                pinlist.append(pin1)
                                for pin_con in pin1._connections.values():
                                    pinlist.append(pin_con)
                                ret[con_core.name]["pins"] = pinlist

                            if "DIN_FROM" in con_core.parameters:
                                ret[con_core.name]["index"] = con_core.parameters[
                                    "DIN_FROM"
                                ].value
                            else:
                                ret[con_core.name]["index"] = 999
                        else:
                            if con_core.type != "module":
                                raise UnexpectedMetadataObjectType(
                                    f"When getting the GPIO data for {self.ref} was expecting {con.ref} to be to a child of a Core"
                                )

            return ret

    def clk_div_param_name(self, clk_id: int, div_id: int) -> str:
        """Returns the name of the clock div parameter for this PS.
        Default is the same format as Ultrascale."""
        return f"PSU__CRL_APB__PL{clk_id}_REF_CTRL__DIVISOR{div_id}"

    def find_clock_divisor(self, clk_id: int, div_id: int) -> int:
        """For a given clock id and divisor id return the clock divisor"""
        clk_odiv = self.clk_div_param_name(clk_id, div_id)
        if clk_odiv in self.parameters:
            divisor = self.parameters[clk_odiv].value
            if divisor is not None:
                return int(divisor)
            else:
                raise ValueError(
                    f"Clock divisor {clk_odiv} for ps {self.ref} has no value"
                )
        else:
            raise ParameterNotFound(
                f"Unable to find a clock divison {clk_odiv} for ps {self.ref}"
            )

    def clk_enable_param_name(self, clk_id: int) -> str:
        """Returns the parameter for the clock enable for clock with id clk_id on this PS.
        Default is the same format as Ultrascale"""
        return f"PSU__FPGA_PL{clk_id}_ENABLE"

    def find_clock_enable(self, clk_id: int) -> bool:
        """Return true if the clock with id clk_id is enabled"""
        param_name = self.clk_enable_param_name(clk_id)
        if param_name in self.parameters:
            value = self.parameters[param_name].value
            if value is not None:
                return int(value) == 1
            else:
                return False
        else:
            raise ParameterNotFound(
                f"unable to find clock clk_id={clk_id} in PS {self.ref} to see if it is enabled"
            )

    @property
    def get_irqs(self) -> Dict[str, Signal]:
        """Returns the list of IRQ signals that can be discovered for this PS"""
        ret: Dict[str, Signal] = {}
        if hasattr(self, "irq"):
            irq = self.irq
            for iname, i in irq.items():
                if iname in self.ports:
                    ret[iname] = self.ports[iname].sig()
        return ret

    @property
    def irq_map(self) -> List[int]:
        """Returns the IRQ map for this PS in the same way that the legacy Pynq metadata is expecting"""
        raw_map: List[int] = []
        for irq in self.irq:
            for base, num in self.irq[irq]:
                for i in range(num):
                    raw_map.append(base + i)
        return raw_map

    def subord_port_to_internal_name(self, subord:SubordinatePort)->str:
        """
        From a subordinate port return the internal naming for that port within
        the processing system (they are different)
        """
        if subord.name == "S_AXI_HPC0_FPD":
            return "SAXIGP0"
        if subord.name == "S_AXI_HPC1_FPD":
            return "SAXIGP1"
        if subord.name == "S_AXI_HP0_FPD":
            return "SAXIGP2"
        if subord.name == "S_AXI_HP1_FPD":
            return "SAXIGP3"
        if subord.name == "S_AXI_HP2_FPD":
            return "SAXIGP4"
        if subord.name == "S_AXI_HP3_FPD":
            return "SAXIGP5"
        if subord.name == "S_AXI_LPD":
            return "SAXIGP6"
        if subord.name == "S_AXI_ACE_FPD":
            return "SAXIACE"
        if subord.name == "S_AXI_ACP_FPD":
            return "SAXIACP"
        return subord.name
