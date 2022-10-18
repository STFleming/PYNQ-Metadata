# Copyright (C) 2022 Xilinx, Inc
# SPDX-License-Identifier: BSD-3-Clause

from pathlib import Path
from typing import Callable, Optional, List, Dict
#from pynqutils.build_utils import Board

from ..models import Module, Core, ProcSysCore


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
                self.t += f"CONFIG.{pname} {{\"{value}\"}} "
            else:
                self.t += f"CONFIG.{pname} "
        
        if len(c.parameters) > 0:
            self.t += "] "
        
        self.t +=  f" [get_bd_cells {c.name}]\n"