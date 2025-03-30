#!/usr/bin/env python3
import subprocess
import sys

# Launch app.py directly
subprocess.Popen([sys.executable, "app.py"])
print("Server started (app.py running in background).")
