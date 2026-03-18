"""Entry point: python -m td_mcp"""

import sys
from pathlib import Path


def bridge_path():
    p = Path(__file__).parent / "td_bridge" / "webserver_callbacks.py"
    print(p)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "bridge-path":
        bridge_path()
        return

    from .server import mcp
    mcp.run()


if __name__ == '__main__':
    main()
