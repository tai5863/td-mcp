"""Entry point: python -m td_mcp"""

import shutil
import sys
from pathlib import Path

BRIDGE_SRC = Path(__file__).parent / "td_bridge" / "webserver_callbacks.py"
DEST_NAME = "td_mcp_callbacks.py"


def install(dest_dir="."):
    dest = Path(dest_dir) / DEST_NAME
    shutil.copy2(BRIDGE_SRC, dest)
    print(f"Installed: {dest.resolve()}")


def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "install":
            install(sys.argv[2] if len(sys.argv) > 2 else ".")
            return
        if cmd == "bridge-path":
            print(BRIDGE_SRC)
            return

    from .server import mcp
    mcp.run()


if __name__ == '__main__':
    main()
