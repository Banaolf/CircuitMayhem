# GAME BUILDER
import sys
import os
import subprocess
import shutil
from pathlib import Path

def folder_exists(parent, child):
    parent = Path(parent)             # accepts str or Path
    return (parent / child).is_dir()  # True only if it exists and is a directory

appdata = Path(os.getenv("LOCALAPPDATA"))
script_pth = (Path(__file__).parent / "error_popup.vbs").resolve()

if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        if not folder_exists(appdata, "CircuitMayhem"):
            meipass = Path(sys._MEIPASS) # get from TEMP extracted from PyInstaller
            shutil.copytree((meipass / "CircuitMayhem"), (appdata / "CircuitMayhem")) # Should copy to appdata
        else:
            subprocess.call(f"python {(appdata / 'CircuitMayhem' / 'scripts' /'game.py')}", shell=True)
    else:
        subprocess.Popen(["wscript.exe", script_pth], shell=True)
        exit(0)
