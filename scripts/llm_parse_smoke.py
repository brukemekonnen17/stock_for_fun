import json
import glob
import statistics
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from apps.api.schemas_llm import parse_llm_json


def main():
    project_root = Path(__file__).parent.parent
    golden_dir = project_root / "tests" / "golden"
    files = sorted(glob.glob(str(golden_dir / "*.out.json")))
    total, ok = 0, 0
    for f in files:
        total += 1
        s = open(f).read()
        ok += 1 if parse_llm_json(s) else 0
    rate = ok / total if total else 1.0
    print(f"parse_rate={rate:.3f} ({ok}/{total})")
    assert rate >= 0.995, "Parse rate below 99.5%"


if __name__ == "__main__":
    main()

