# Copyright (C) 2022 Xilinx, Inc
# SPDX-License-Identifier: BSD-3-Clause
from pathlib import Path
from typing import Callable, Optional, List, Dict

from ..models import Module, Core, ProcSysCore
from ..models import ManagerPort, StreamPort, BusConnection
from ..models import ClkPort, RstPort, ScalarPort
from ..models import ManagerPort

from .bd_target import BDTarget

class XsaTarget(BDTarget):
    
    def __init__(
        self,
        md:Module,
        board,
        ip_libraries:List[str]=[],
        board_repos:List[str]=[],
        preset:Dict[str,str]={},
        design_name:str = "design_1",
        project_name:str = "project_1",
        tool_version:str = "2022.1"

    ) -> None:
        """ 
            From a metadata object generate a build script that will produce an
            equivalent XSA from Vivado
        """
        super().__init__(md=md, board=board, ip_libraries=ip_libraries, board_repos=board_repos, preset=preset, design_name=design_name, project_name=project_name, tool_version=tool_version)
        self.t += f"set_property synth_checkpoint_mode None [get_files  ./{self.project_name}.srcs/sources_1/bd/{self.design_name}/{self.design_name}.bd]\n"
        self.t += f"generate_target all [get_files ./{self.project_name}.srcs/sources_1/bd/{self.design_name}/{self.design_name}.bd]\n"
        self.t += f"export_ip_user_files -of_objects [get_files ./{self.project_name}.srcs/sources_1/bd/{self.design_name}/{self.design_name}.bd] -no_script -sync -force -quiet\n"

        self.t += f"launch_runs synth_1\n"
        self.t += f"wait_on_runs synth_1\n"

        self.t += f"launch_runs impl_1 -to_step write_bitstream -jobs 4\n"
        self.t += f"wait_on_runs impl_1\n"

        self.t += f"write_hw_platform -fixed -include_bit -force -file {self.board.name}_{self.md.name}.xsa"
