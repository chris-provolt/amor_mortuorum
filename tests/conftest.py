import sys
from pathlib import Path

# Ensure 'src' is on sys.path for test imports without installing the package
ROOT = Path(__file__).resolve().parents[1]
src = ROOT / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))
