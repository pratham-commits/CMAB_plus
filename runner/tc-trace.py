import logging
import os
import subprocess
import time
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s tc-trace: %(message)s",
)
logger = logging.getLogger(__name__)

ETHERNET = "eth0"
INTERVAL = float(os.getenv("INTERVAL", "0.01"))
# Trace RTT=0 marks handover in isl-trace.csv; upstream used 100% loss (very harsh on high ABR).
HANDOVER_LOSS_PERCENT = os.getenv("HANDOVER_LOSS_PERCENT", "100")


def _tc(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(args, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, args, result.stdout, result.stderr
        )
    return result


def tc_del() -> None:
    _tc(["tc", "qdisc", "del", "dev", ETHERNET, "root"], check=False)


def tc_init() -> None:
    """Build HTB + netem from scratch. Safe after docker restart (same netns, stale qdisc)."""
    tc_del()
    _tc(
        [
            "tc",
            "qdisc",
            "add",
            "dev",
            ETHERNET,
            "root",
            "handle",
            "1:",
            "htb",
            "default",
            "1",
        ]
    )
    _tc(
        [
            "tc",
            "class",
            "add",
            "dev",
            ETHERNET,
            "parent",
            "1:",
            "classid",
            "1:1",
            "htb",
            "rate",
            "100mbit",
            "ceil",
            "50mbit",
        ]
    )
    _tc(
        [
            "tc",
            "qdisc",
            "add",
            "dev",
            ETHERNET,
            "parent",
            "1:1",
            "handle",
            "10:",
            "netem",
            "delay",
            "40ms",
            "loss",
            "0.1%",
        ]
    )
    logger.info("tc init OK on %s", ETHERNET)


def set_static_delay(rtt: int) -> None:
    loss = "1%"
    ceil = "50mbit"
    if rtt == 0 or rtt == -1:
        rtt = 100
        loss = f"{HANDOVER_LOSS_PERCENT}%"
        ceil = "20mbit"

    _tc(
        [
            "tc",
            "class",
            "change",
            "dev",
            ETHERNET,
            "parent",
            "1:",
            "classid",
            "1:1",
            "htb",
            "rate",
            "100mbit",
            "ceil",
            ceil,
        ]
    )
    _tc(
        [
            "tc",
            "qdisc",
            "change",
            "dev",
            ETHERNET,
            "parent",
            "1:1",
            "handle",
            "10:",
            "netem",
            "delay",
            f"{rtt}ms",
            "loss",
            loss,
        ]
    )


def tc_reset() -> None:
    _tc(
        [
            "tc",
            "class",
            "change",
            "dev",
            ETHERNET,
            "parent",
            "1:",
            "classid",
            "1:1",
            "htb",
            "rate",
            "100mbit",
            "ceil",
            "50mbit",
        ]
    )
    _tc(
        [
            "tc",
            "qdisc",
            "change",
            "dev",
            ETHERNET,
            "parent",
            "1:1",
            "handle",
            "10:",
            "netem",
            "delay",
            "40ms",
            "loss",
            "0.1%",
        ]
    )


if __name__ == "__main__":
    tc_init()

    latency_trace: dict[str, int] = {}
    with open("/trace/trace.csv", "r") as f:
        for count, line in enumerate(f):
            if count == 0:
                continue
            since, _relative, rtt = line.strip("\n").split(",")
            latency_trace[since] = int(float(rtt))

    init = datetime.now()
    logger.info(
        "trace loaded: %d keys, interval=%ss, handover_loss=%s%%",
        len(latency_trace),
        INTERVAL,
        HANDOVER_LOSS_PERCENT,
    )

    while True:
        time.sleep(INTERVAL)
        relative = datetime.now() - init
        closest = min(
            latency_trace, key=lambda x: abs(float(x) - relative.total_seconds())
        )
        rtt = latency_trace[closest]
        print(closest, rtt, flush=True)
        try:
            set_static_delay(rtt)
        except subprocess.CalledProcessError as exc:
            logger.error("tc update failed: %s %s", exc.stderr, exc.stdout)
            tc_init()
            set_static_delay(rtt)
