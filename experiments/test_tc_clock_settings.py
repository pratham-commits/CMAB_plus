"""Clock shaper defaults stay on the paper profile. A set rate does not reopen at handover."""

import importlib.util
import os
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "runner" / "tc.py"


def load():
    spec = importlib.util.spec_from_file_location("tc_clock_under_test", PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    saved = {key: os.environ.get(key) for key in list(os.environ) if key.startswith("CLOCK_")}
    for key in list(os.environ):
        if key.startswith("CLOCK_"):
            del os.environ[key]
    try:
        tc = load()
        tc.load_config()
        normal_tbf, normal_netem = tc.normal_change_args()
        hand_tbf, hand_netem = tc.handover_change_args()
        assert normal_tbf[normal_tbf.index("rate") + 1] == "100mbit"
        assert normal_tbf[normal_tbf.index("latency") + 1] == "40ms"
        assert hand_tbf[hand_tbf.index("rate") + 1] == "50mbit"
        assert hand_tbf[hand_tbf.index("latency") + 1] == "100ms"
        assert normal_netem[normal_netem.index("delay") + 1] == "40ms"
        assert normal_netem[normal_netem.index("loss") + 1] == "0.1%"
        assert hand_netem[hand_netem.index("delay") + 1] == "100ms"
        assert hand_netem[hand_netem.index("loss") + 1] == "1%"
        assert tc.get_handover_time() == {12, 27, 42, 57}

        os.environ["CLOCK_RATE_MBIT"] = "4"
        os.environ["CLOCK_HANDOVER_LOSS_PERCENT"] = "20"
        tc.load_config()
        normal_tbf, _ = tc.normal_change_args()
        hand_tbf, hand_netem = tc.handover_change_args()
        assert normal_tbf[normal_tbf.index("rate") + 1] == "4mbit"
        assert hand_tbf[hand_tbf.index("rate") + 1] == "4mbit"
        assert hand_netem[hand_netem.index("loss") + 1] == "20%"
    finally:
        for key in list(os.environ):
            if key.startswith("CLOCK_"):
                del os.environ[key]
        for key, value in saved.items():
            if value is not None:
                os.environ[key] = value
    print("tc clock settings: all assertions passed")


if __name__ == "__main__":
    main()
