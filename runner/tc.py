import os
import time
from datetime import datetime
import subprocess


HANDOVER_SECOND = [12, 27, 42, 57]
ETHERNET = "eth0"

# Paper clock, used when no CLOCK_* env is set: 100 mbit / 0.1% loss,
# and on seconds 12/27/42/57 a 50 mbit / 100 ms / 1% loss bump.
NORMAL_RATE_MBIT = 100.0
HANDOVER_RATE_MBIT = 50.0
NORMAL_LOSS_PERCENT = 0.1
HANDOVER_LOSS_PERCENT = 1.0
NORMAL_DELAY_MS = 40
HANDOVER_DELAY_MS = 100
HANDOVER_DURATION = 0


def _env_float(name: str):
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return None
    value = float(raw)
    if value < 0:
        raise ValueError(f"{name} must be >= 0, got {raw}")
    return value


def _env_int(name: str):
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return None
    value = int(raw)
    if value < 0:
        raise ValueError(f"{name} must be >= 0, got {raw}")
    return value


def load_config() -> None:
    """Read CLOCK_* from the environment. Defaults match the paper clock shaper."""
    global NORMAL_RATE_MBIT, HANDOVER_RATE_MBIT
    global NORMAL_LOSS_PERCENT, HANDOVER_LOSS_PERCENT
    global NORMAL_DELAY_MS, HANDOVER_DELAY_MS, HANDOVER_DURATION

    normal_rate = _env_float("CLOCK_RATE_MBIT")
    handover_rate = _env_float("CLOCK_HANDOVER_RATE_MBIT")
    NORMAL_RATE_MBIT = 100.0 if normal_rate is None else normal_rate
    if NORMAL_RATE_MBIT <= 0:
        raise ValueError("CLOCK_RATE_MBIT must be > 0")
    # A slower normal rate must not jump back to 50 mbit during the handover.
    if handover_rate is None:
        HANDOVER_RATE_MBIT = 50.0 if normal_rate is None else NORMAL_RATE_MBIT
    else:
        HANDOVER_RATE_MBIT = handover_rate
    if HANDOVER_RATE_MBIT <= 0:
        raise ValueError("CLOCK_HANDOVER_RATE_MBIT must be > 0")

    normal_loss = _env_float("CLOCK_LOSS_PERCENT")
    handover_loss = _env_float("CLOCK_HANDOVER_LOSS_PERCENT")
    NORMAL_LOSS_PERCENT = 0.1 if normal_loss is None else normal_loss
    HANDOVER_LOSS_PERCENT = 1.0 if handover_loss is None else handover_loss

    normal_delay = _env_int("CLOCK_DELAY_MS")
    handover_delay = _env_int("CLOCK_HANDOVER_DELAY_MS")
    NORMAL_DELAY_MS = 40 if normal_delay is None else normal_delay
    HANDOVER_DELAY_MS = 100 if handover_delay is None else handover_delay

    duration = _env_int("CLOCK_HANDOVER_DURATION")
    HANDOVER_DURATION = 0 if duration is None else duration


def rate_token(mbit: float) -> str:
    if float(mbit).is_integer():
        return f"{int(mbit)}mbit"
    return f"{mbit}mbit"


def loss_token(percent: float) -> str:
    if float(percent).is_integer():
        return f"{int(percent)}%"
    return f"{percent}%"


def get_handover_time() -> set:
    handover = []
    for t in HANDOVER_SECOND:
        for i in range(HANDOVER_DURATION + 1):
            handover.append(t - i if t - i >= 0 else t - i + 60)
            handover.append(t + i if t + i < 60 else t + i - 60)
    return set(handover)


def is_now_handover(now: int, handover: set) -> bool:
    return now in handover


def _tbf(action: str, rate: str, latency_ms: int) -> list:
    return [
        "tc", "qdisc", action, "dev", ETHERNET, "root", "handle", "1:",
        "tbf", "rate", rate, "burst", "16kbit", "latency", f"{latency_ms}ms",
    ]


def _netem(action: str, delay_ms: int, jitter_ms: int, loss: str) -> list:
    return [
        "tc", "qdisc", action, "dev", ETHERNET, "parent", "1:1", "handle", "10:",
        "netem", "delay", f"{delay_ms}ms", f"{jitter_ms}ms", "25%", "loss", loss,
    ]


def normal_change_args() -> tuple:
    rate = rate_token(NORMAL_RATE_MBIT)
    loss = loss_token(NORMAL_LOSS_PERCENT)
    return (
        _tbf("change", rate, NORMAL_DELAY_MS),
        _netem("change", NORMAL_DELAY_MS, 1, loss),
    )


def handover_change_args() -> tuple:
    rate = rate_token(HANDOVER_RATE_MBIT)
    loss = loss_token(HANDOVER_LOSS_PERCENT)
    return (
        _tbf("change", rate, HANDOVER_DELAY_MS),
        _netem("change", HANDOVER_DELAY_MS, 10, loss),
    )


def apply_pair(pair: tuple) -> None:
    for args in pair:
        subprocess.check_output(args)


def set_delay() -> None:
    apply_pair(handover_change_args())


def tc_reset() -> None:
    apply_pair(normal_change_args())


def tc_init() -> None:
    rate = rate_token(NORMAL_RATE_MBIT)
    subprocess.check_output(_tbf("add", rate, NORMAL_DELAY_MS))
    subprocess.check_output([
        "tc", "qdisc", "add", "dev", ETHERNET, "parent", "1:1", "handle", "10:",
        "netem", "delay", f"{NORMAL_DELAY_MS}ms",
    ])


def tc_del() -> None:
    subprocess.check_output(["tc", "qdisc", "del", "dev", ETHERNET, "root"])


if __name__ == "__main__":
    load_config()
    print(
        "clock shaper: normal={} {}ms loss={} handover={} {}ms loss={} duration={}".format(
            rate_token(NORMAL_RATE_MBIT),
            NORMAL_DELAY_MS,
            loss_token(NORMAL_LOSS_PERCENT),
            rate_token(HANDOVER_RATE_MBIT),
            HANDOVER_DELAY_MS,
            loss_token(HANDOVER_LOSS_PERCENT),
            HANDOVER_DURATION,
        ),
        flush=True,
    )
    tc_init()
    handover = get_handover_time()

    while True:
        now = datetime.now().second
        if is_now_handover(now, handover):
            set_delay()
        else:
            tc_reset()

        time.sleep(0.1)
