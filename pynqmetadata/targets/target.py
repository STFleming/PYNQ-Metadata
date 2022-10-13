from pathlib import Path
from typing import Callable, Optional

from pynqmetadata import Module


def target(md: Module, apply:Callable[[Module], str], file:Optional[Path]=None, instr:Optional[str]=None)->Optional[str]:
    """ 
    Applies a target pass to the metadata object, if a file is provided it will
    save it to the file. Otherwise it will return a string. 

    If an instr is provided then the output from the pass will be appeneded to the string.    
    """
    s = apply(md)
    if instr is not None:
        s = instr + s
    if file is not None:
        try:
            f = open(file, "w")
            f.write(s)
            f.close()
        except:
            raise RuntimeError(f"Unable to open file {file} to save the target")
    else:
        return s
