"""L2A has no CMAB flag. Loading the capacity batch must not crash on that."""

import json
import sys
import types
from datetime import timezone
from pathlib import Path

pytz = types.ModuleType("pytz")
pytz.timezone = lambda _name: timezone.utc
sys.modules["pytz"] = pytz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runner"))
from config import Experiment  # noqa: E402


def main() -> None:
    batch = json.loads((ROOT / "experiments" / "batch-capacity-decision.json").read_text())
    ids = []
    for obj in batch:
        exp = Experiment(obj)
        ids.append(exp.EXPERIMENT_ID)
        print(exp.ABR_ALGORITHM, exp.CMAB_HARDENED, exp.EXPERIMENT_ID)
    assert ids[0].startswith("abrCMAB-")
    assert ids[1].startswith("abrCMABPlus-")
    assert ids[2].startswith("abrL2A-")
    assert len(set(ids)) == 3
    print("batch ids ok")


if __name__ == "__main__":
    main()
