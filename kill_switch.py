"""Create or remove the V5 entry kill switch."""
import argparse
from pathlib import Path
from config import KILL_SWITCH_FILE
p = argparse.ArgumentParser()
p.add_argument("action", choices=["on", "off"])
a = p.parse_args()
path = Path(KILL_SWITCH_FILE)
if a.action == "on":
    path.write_text("KILL SWITCH ACTIVE: new entries blocked.\\n")
    print(f"Kill switch ON: {path}")
else:
    if path.exists(): path.unlink()
    print("Kill switch OFF. Existing exchange orders/positions were NOT changed.")
