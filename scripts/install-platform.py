#!/usr/bin/env python3
"""Install all Aegis platform Python packages."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGES = ["execution", "options", "market-maker", "analytics", "aegis-quant"]


def main() -> int:
    for pkg in PACKAGES:
        path = ROOT / pkg
        print(f"Installing {pkg}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", str(path)])
    print("All platform packages installed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
