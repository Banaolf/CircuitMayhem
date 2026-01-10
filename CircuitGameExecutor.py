import sys
import os
import arcade
import json
import subprocess
import shutil
from pathlib import Path

def folder_exists(parent, child):
    parent = Path(parent)
    return (parent / child).is_dir()

appdata = Path(os.getenv("LOCALAPPDATA"))

if __name__ == "__main__":
    # --- PART 1: THE MINI-INTERPRETER LOGIC ---
    # If the EXE is called with a .py file as an argument, run it.
    if len(sys.argv) > 1 and sys.argv[1].endswith(".py"):
        script_pth = Path(sys.argv[1])
        
        # 1. Add the script's folder to the search path so 'import' works
        sys.path.insert(0, str(script_pth.parent))
        
        # 2. Add the root CircuitMayhem folder to path too (if you import from 'objs')
        root_dir = script_pth.parent.parent
        if str(root_dir) not in sys.path:
            sys.path.append(str(root_dir))

        # 3. Execute the script
        with open(script_pth, "r") as f:
            exec(f.read(), {"__name__": "__main__"})
        sys.exit(0)

    # --- PART 2: THE INSTALLER/LAUNCHER LOGIC ---
    if getattr(sys, 'frozen', False):
        target_dir = appdata / "CircuitMayhem"
        
        if not target_dir.exists():
            # Get the temp folder where PyInstaller extracted your files
            meipass = Path(sys._MEIPASS) 
            # Copy everything to LocalAppData
            shutil.copytree((meipass / "CircuitMayhem"), target_dir)
        
        # Now launch the game by calling THIS SAME EXE with the script path
        game_script = target_dir / "scripts" / "game.py"
        subprocess.call([sys.executable, str(game_script)])
    else:
        # Development mode logic
        vbs_script = (appdata / "CircuitMayhem" / "error_popup.vbs")
        subprocess.Popen(["wscript.exe", str(vbs_script)], shell=True)
        sys.exit(0)