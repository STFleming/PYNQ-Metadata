# Copyright (C) 2022 Xilinx, Inc
# SPDX-License-Identifier: BSD-3-Clause

import os

from pynqmetadata.frontends import Metadata
from pynqmetadata.targets import block_design_target, create_bd_project, target

TEST_DIR = os.path.dirname(__file__)


#def test_vivado_target_reziser():
#    """
#    Test to see if no errors are encountered when generating a tcl'd version of the project 
#    """
#    md = Metadata(f"{TEST_DIR}/hwhs/resizer.hwh")
#    tcl = create_bd_project(part="testpart",
#                            board="testboard", 
#                            boardrepo=["board_loc/one", "board_loc/two"],
#                            ip_libraries=["ip_lib/one", "ip_lib/two"] 
#                            )
#    tcl = target(md=md, apply=block_design_target, instr=tcl)
    

