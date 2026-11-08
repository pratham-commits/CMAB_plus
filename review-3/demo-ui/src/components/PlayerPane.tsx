import { useEffect, useRef, useState } from "react";
import type { PlayerEntry, TimelinePayload } from "../lib/types";
import { isStalling, sampleAt } from "../lib/playback";
import { qualityCaption, tierForBitrate } from "../lib/quality";

type Props = {
  entry: PlayerEntry | undefined;
  demoTimeS: number;
  playing: boolean;
  accent: string;
};

export function PlayerPane({ entry, demoTimeS, playing, accent }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const loadedFile = useRef<string | null>(null);
  const [timeline, setTimeline] = useState<TimelinePayload | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setTimeline(null);
    setLoadError(null);
    if (!entry || entry.status !== "ok" || !entry.timeline) {
      return;
    }
    fetch(`./${entry.timeline}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: TimelinePayload) => {
        if (!cancelled) setTimeline(data);
      })
      .catch((err: Error) => {
        if (!cancelled) setLoadError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [entry]);

  const sample = timeline ? sampleAt(timeline.samples, demoTimeS) : null;
  const stalling = isStalling(sample);
  const tier = tierForBitrate(sample?.bitrate);
  const videoSrc = `./${tier.file}`;
  const shouldPlay = playing && !stalling && !!timeline;

  // Load / switch ladder encodes; keep the same playhead across rung changes.
  useEffect(() => {
    const v = videoRef.current;
    if (!v || entry?.status !== "ok") return;
    if (loadedFile.current === tier.file) return;

    const resumeAt = loadedFile.current ? v.currentTime || 0 : 0;
    loadedFile.current = tier.file;
    v.src = videoSrc;
    v.load();

    const onReady = () => {
      try {
        if (resumeAt > 0 && Number.isFinite(resumeAt)) {
          v.currentTime = resumeAt;
        }
      } catch {
        /* ignore seek errors during rapid switches */
      }
      if (shouldPlay) {
        v.play()?.catch(() => undefined);
      } else {
        v.pause();
      }
    };
    v.addEventListener("loadedmetadata", onReady, { once: true });
    return () => v.removeEventListener("loadedmetadata", onReady);
  }, [tier.file, videoSrc, shouldPlay, entry?.status]);

  // Play / pause / stall freeze — never reset the playhead here.
  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;
    if (!shouldPlay) {
      v.pause();
      return;
    }
    v.play()?.catch(() => undefined);
  }, [shouldPlay]);

  // Reset playhead only when the session cell changes (new entry).
  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;
    v.currentTime = 0;
  }, [entry?.timeline]);

  const metrics = entry?.metrics ?? timeline?.metrics;
  const label = entry?.player ?? "—";
  const caption = qualityCaption(tier, sample?.bitrate ?? null);

  return (
    <section className="pane" style={{ ["--pane-accent" as string]: accent }}>
      <header className="pane__head">
        <h3>{label}</h3>
        {metrics ? (
          <div className="pane__hud" title="Session averages (trim first 20%)">
            <span>
              Live latency <b>{metrics.latency_s.toFixed(2)}s</b>
            </span>
            <span>
              Time spent rebuffering <b>{metrics.rebuffer_pct.toFixed(1)}%</b>
            </span>
            <span>
              Video quality <b>{Math.round(metrics.bitrate_kbps)} kbps</b>
            </span>
          </div>
        ) : (
          <div className="pane__hud pane__hud--muted">no metrics</div>
        )}
      </header>

      <div className={`pane__stage ${stalling ? "pane__stage--stall" : ""}`}>
        {entry?.status === "ok" ? (
          <>
            <video
              ref={videoRef}
              muted
              playsInline
              loop
              preload="auto"
              className="pane__video"
              style={{ filter: tier.filter }}
            />
            <div className="pane__broadcast" aria-hidden>
              <span className="pane__live-tag">LIVE</span>
              <span className="pane__sport">Cricket · Sunshine Coast</span>
            </div>
            <div className={`pane__quality pane__quality--${tier.label.toLowerCase()}`} aria-live="polite">
              {caption}
            </div>
            {stalling && (
              <div className="pane__overlay">
                <span className="pane__freeze">Rebuffering…</span>
                <span className="pane__buf">
                  Playback buffer {sample?.buffer.toFixed(3) ?? "0"}s
                </span>
              </div>
            )}
          </>
        ) : (
          <div className="pane__placeholder">
            <p>Placeholder</p>
            <small>{entry?.note || "Session JSON not available locally"}</small>
          </div>
        )}
        {loadError && <div className="pane__error">Timeline: {loadError}</div>}
      </div>

      <footer className="pane__live">
        {sample ? (
          <>
            <span>
              Playback buffer <b>{sample.buffer.toFixed(2)}s</b>
            </span>
            <span>
              Live latency <b>{sample.latency.toFixed(2)}s</b>
            </span>
            <span>
              Bitrate <b>{Math.round(sample.bitrate)} kbps</b>
            </span>
            <span>
              Ladder <b>
                {tier.kbps} ({tier.label})
              </b>
            </span>
          </>
        ) : (
          <span className="pane__hud--muted">awaiting timeline</span>
        )}
      </footer>
    </section>
  );
}
