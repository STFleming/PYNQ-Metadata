# Copyright (C) 2022 Xilinx, Inc
# SPDX-License-Identifier: BSD-3-Clause

from pathlib import Path
from typing import Callable, Optional, List, Dict

from ..models import Module, Core, ProcSysCore
from ..models import ManagerPort, StreamPort, BusConnection
from ..models import ClkPort, RstPort, ScalarPort
from ..models import ManagerPort


class BDTarget:

    def __init__(
        self,
        md:Module,
        board,
        ip_libraries:List[str]=[], 
        board_repos:List[str]=[], 
        preset:Dict[str,str]={},
        design_name:str = "design_1",
        project_name:str = "project_1"
    ) -> None:
        """ 
            From a module create the tcl string that can regenerate the block diagram of the system.
            Input arguments:
            -----------------
             * libraries : a list of directories where the IP core libraries will live on the target build machine
             * board_repos : a list of directories where the board metadata is kept on the target build machine
             * preset : a list of board specific presets that need to be overwritten when generating the parameters
        """
        self.t = "# Auto-generated build script from pynqmetadata\n"
        self.md = md
        self.board = board
        self.preset = board.get_preset_dict()
        self.ip_libraries = ip_libraries
        self.board_repos = board_repos
        self.design_name = design_name
        self.project_name = project_name
        self._create_project()
        self._populate_cores()
        self._populate_bus_connections()

        for bus in self.md.busses.values():
            if isinstance(bus._src_port, ManagerPort):
                self._resolve_addressing(bus)

        self._save_and_make_wrapper()


    def str(self)->str:
        return self.t

    def _create_project(self)->None:
        """ Generates the tcl to create the project """

        # Add all the board repos
        for b in self.board_repos:
            self.t += f"set_param board.repoPaths {b}\n"

        self.t += f"""
create_project -force {self.project_name} ./ -part {self.board.part_name}
set_property board_part {self.board.board_typestring()} [current_project]
"""

        # Add all the ip libraries
        for lib in self.ip_libraries:
            self.t += f"set_property ip_repo_paths {lib} [current_project]\n"
        self.t += f"update_ip_catalog\n"

        self.t += f"""
create_bd_design {self.design_name}
update_compile_order -fileset sources_1 
"""       

    def _populate_cores(self)->None:
        """ Walks over the cores in the module and generates the tcl
        commands for instantiating them """
        for c in self.md.blocks.values():
            if isinstance(c, Core):
                self._add_core(c)

    def _add_core(self, c:Core)->None:
        """ generates the tcl command to instantiate a core """
        self.t += f"create_bd_cell -type ip -vlnv {c.vlnv.str} {c.name}\n"
        if isinstance(c, ProcSysCore):
            self.t += f'apply_bd_automation -rule xilinx.com:bd_rule:{c.vlnv.name} -config {{apply_board_preset "1"}} [get_bd_cells {c.name}]\n' 
        self._apply_core_properties(c)

    def _apply_core_properties(self, c:Core)->None:
        """ Walks the parameter space of a core and instantiates the properties for it. """
        self.t += "set_property -quiet -dict [ list "
        for pname,pval in c.parameters.items():
            if pval != "none" and pval != "undef":
                value = pval.value
                if pname in self.preset:
                    value = self.preset[pname]
                self.t += f"CONFIG.{pname} {{{value}}} "
            else:
                self.t += f"CONFIG.{pname} "
        
        if len(c.parameters) > 0:
            self.t += "] "
        
        self.t +=  f" [get_bd_cells {c.name}]\n"

    def _populate_bus_connections(self)->None:
        """ Populates connections from Managers->Subordinates.
        uses the connection automation tcl command """
        for bus in self.md.busses.values():
            if isinstance(bus._src_port, ManagerPort):
                self._add_connection(bus)
            if isinstance(bus._src_port, StreamPort):
                if bus._src_port.driver:
                    self._add_connection(bus)

                if bus._src_port.vlnv.name == "axis_switch":
                    if not bus._src_port.driver:
                        self._add_connection(bus)

            if isinstance(bus._src_port, ScalarPort) or isinstance(bus._src_port, ClkPort) or isinstance(bus._src_port, RstPort) :
                if bus._src_port.driver:
                    self._add_connection(bus)

    def _add_connection(self, bus:BusConnection)->None:
        """ Generates the tcl command from the bus driver to the destination """
        src_name = f"{bus._src_port._parent.name}/{bus._src_port.name}"
        dst_name = f"{bus._dst_port._parent.name}/{bus._dst_port.name}"
        if isinstance(bus._src_port, ClkPort) or isinstance(bus._src_port, RstPort) or isinstance(bus._src_port,ScalarPort):
            self.t += f"connect_bd_net [get_bd_pins {src_name}] [get_bd_pins {dst_name}]\n"
        else:
            self.t += f"connect_bd_intf_net -boundary_type upper [get_bd_intf_pins {src_name}] [get_bd_intf_pins {dst_name}]\n"

    def _resolve_addressing(self, bus:BusConnection)->None:
        """ For all the memory mapped peripherals, resolve their address space """
        if not isinstance(bus._src_port, ManagerPort):
            raise RuntimeError(f"Cannot resolve addressing on non-manager port {bus._src_port.ref}")
        else:
            for mem_name, mem in bus._src_port.addrmap.items():
                self.t += "assign_bd_address -target_address_space "
                if isinstance(bus._src_port._parent, ProcSysCore):
                    self.t += f"/{bus._src_port._parent.name}/Data"
                elif bus._src_port._parent.vlnv.name == "axi_dma" or bus._src_port._parent.vlnv.name == "axi_vdma":
                    label = bus._src_port.name.split("_")[-1]
                    self.t += f"/{bus._src_port._parent.name}/Data_{label}" 
                else:
                    self.t += f"/{bus._src_port._parent.name}/Data_{bus._src_port.name}"

                self.t += f" [get_bd_addr_segs "

                subport = bus._src_port._addrmap_obj[mem_name]
                subport_parent = subport._parent
                if isinstance(subport_parent, ProcSysCore):
                    internal_portname = subport_parent.subord_port_to_internal_name(subport)
                    self.t += f"{subport_parent.name}/{internal_portname}/{mem['block']}"
                else:
                    self.t += f"{subport_parent.name}/{subport_parent.name}/{mem['block']}"
                self.t += "]\n"

    def _save_and_make_wrapper(self):
        """ Closes up the block diagram and creates the HDL wrapper """
        self.t += "update_compile_order -fileset sources_1\n"
        self.t += "save_bd_design\n"

        self.t += f"make_wrapper -files [get_files ./{self.project_name}.srcs/sources_1/bd/{self.design_name}/{self.design_name}.bd] -top\n"
        self.t += f"add_files -norecurse ./{self.project_name}.gen/sources_1/bd/{self.design_name}/hdl/{self.design_name}_wrapper.v\n"
        return

