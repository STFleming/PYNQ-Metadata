# Copyright (C) 2022 Xilinx, Inc
# SPDX-License-Identifier: BSD-3-Clause

from ..models import Module, Core
from ..models import Vlnv
import json
import pathlib

def tool_version_pass(md:Module, tool_version="2022.1")->Module:
    """ Walks over the metadata and attempts to transform it to be compatible
    with a given tool version 

    This is a best effort transformation, and passing the metadata through
    this is not guaranteed to transform it in a way to meet the desired tool 
    spec.

    """
    try:
        version_file_loc = pathlib.Path(__file__).parent.resolve() / "version_upgrade.json"
        version_file = open(version_file_loc, "r") 
        vlnv_dict = json.loads(version_file.read()) 
    except:
        raise RuntimeError(f"Unable to load the IP version file {version_file_loc} to migrate IP to specific tool instance")
     
    for block in md.blocks.values():
        if isinstance(block, Core):
            if block.vlnv.name in vlnv_dict[tool_version]:
                upgrd = vlnv_dict[tool_version][block.vlnv.name]
                new_vlnv = Vlnv(vendor=upgrd["vendor"], 
                                library=upgrd["library"], 
                                name=upgrd["name"], 
                                version=(upgrd["version"][0],upgrd["version"][1])) 
                block.vlnv = new_vlnv
        else:
            if isinstance(block, Module):
                tool_version_target(md=block, tool_version=tool_version)

    return md
