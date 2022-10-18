from typing import List

from ..models import Core, Module, ProcSysCore


def create_bd_project(
                    part:str, 
                    board:str, 
                    design_name:str = "design_1",
                    project_name:str = "project_1",
                    boardrepo:List[str]=[], 
                    ip_libraries:List[str]=[]
                )->str:

    """ Generates the tcl to create the project """
    t = "# Auto=generated build from from pynqmetadata\n"
    
    # Add all the board repositories
    for b in boardrepo:
        t += f"set_param board.repoPaths {b}\n"
    
    t += """
create_project -force {project_name} ./ -part {part}
set_property board_part {board} [current_project]    
    """

    # Add all the libraries
    for lib in ip_libraries:
        t += f"set_property ip_repo_paths {lib} [current_project]" 
    t += f"update_ip_catalog\n"

    t += """
create_bd_design '{design_name}'
update_compile_order -fileset sources_1 
    """
    return t
    
def block_design_target(md: Module)->str:
    """ From a module instantiate tcl that will generate the block design """
    s = ""
    for c in md.blocks.values():
        if isinstance(c, Core):    
            s += _add_core(c)
    return s

def _add_core(c:Core)->str:
    """Adds a core to the tcl script"""
    s = f"create_bd_cell -type ip -vlnv {c.vlnv.str} {c.name}\n"
    # if it is a processing system apply the board presets
    if isinstance(c, ProcSysCore):
        s += f'apply_bd_automation -rule xilinx.com:bd_rule:{c.vlnv.name} -config {{apply_board_preset "1"}} [get_bd_cells {c.name}]\n' 
    s += _apply_core_properties(c)
    return s

def _apply_core_properties(c:Core)->str:
    """ Applies the parameter space of IP cores """
    pass

    
