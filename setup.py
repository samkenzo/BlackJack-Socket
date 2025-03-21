import os
import sys
from subprocess import run

# Ensure we are using the correct Python executable
python_exec = sys.executable

# Set the correct delimiter for --add-data based on the operating system
if sys.platform == "win32":
    add_data = "cards;cards"
else:
    add_data = "cards:cards"

# Define the command to package the blackjack client
command = [
    python_exec, "-m", "PyInstaller",
    "--onefile",       
    "--windowed",      
    "--add-data", add_data,  
    "--hidden-import=json",  # Add necessary imports
    "--hidden-import=socket",
    "--hidden-import=tkinter",
    "blackjack_client.py"
]


# Run the PyInstaller command
run(command)
