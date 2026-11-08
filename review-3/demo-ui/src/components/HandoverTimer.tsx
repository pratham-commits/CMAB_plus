import { useEffect, useState } from "react";

const SLOTS = [12, 27, 42, 57];
const PERIOD = 15;

function nextSlotInfo(now = new Date()) {
  const sec = now.getSeconds() + now.getMilliseconds() / 1000;
  let next = SLOTS.find((s) => s > sec);
  let wrapped = false;
  if (next == null) {
    next = SLOTS[0] + 60;
    wrapped = true;
  }
  const remaining = next - sec;
  const progress = 1 - remaining / PERIOD;
  const wallSlot = wrapped ? SLOTS[0] : next;
  return { remaining, progress, wallSlot, sec };
}

type Props = {
  demoTimeS: number;
  playing: boolean;
};

export function HandoverTimer({ demoTimeS, playing }: Props) {
  const [wall, setWall] = useState(() => nextSlotInfo());
  const [pulse, setPulse] = useState(false);

  useEffect(() => {
    if (!playing) {
      setPulse(false);
      return;
    }
    const id = window.setInterval(() => {
      const info = nextSlotInfo();
      setWall(info);
      const near = SLOTS.some(
        (s) => Math.abs(info.sec - s) < 0.35 || Math.abs(info.sec - (s + 60)) < 0.35
      );
      setPulse(near);
    }, 50);
    return () => window.clearInterval(id);
  }, [playing]);

  const demoSecInMin = ((demoTimeS % 60) + 60) % 60;
  const demoNear = SLOTS.some((s) => Math.abs(demoSecInMin - s) < 0.4);
  const activePulse = playing && (pulse || demoNear);

  return (
    <div className={`handover ${activePulse ? "handover--pulse" : ""}`}>
      <div className="handover__eyebrow">15 s LEO handover timer</div>
      <div className="handover__row">
        <div className="handover__countdown">
          <span className="handover__num">{wall.remaining.toFixed(1)}</span>
          <span className="handover__unit">s to slot</span>
        </div>
        <div className="handover__meta">
          <div>
            Next wall slot <strong>:{String(Math.floor(wall.wallSlot)).padStart(2, "0")}</strong>
            {!playing && <span className="handover__paused"> · frozen while paused</span>}
          </div>
          <div className="handover__slots">Slots each minute: {SLOTS.map((s) => `:${s}`).join(" · ")}</div>
          <div className="handover__demo">
            Demo time {demoTimeS.toFixed(1)}s · in-minute {demoSecInMin.toFixed(1)}s
          </div>
        </div>
      </div>
      <div className="handover__track" aria-hidden>
        <div className="handover__fill" style={{ width: `${Math.min(100, wall.progress * 100)}%` }} />
        {SLOTS.map((s) => (
          <span key={s} className="handover__tick" style={{ left: `${((s % PERIOD) / PERIOD) * 100}%` }} />
        ))}
      </div>
    </div>
  );
}
