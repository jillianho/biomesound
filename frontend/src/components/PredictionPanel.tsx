"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  predictTrajectory,
  predictAudio,
  getAudioUrl,
  type BiomeState,
  type PredictEvent,
  type PredictResponse,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const ROLE_RGB: Record<string, string> = {
  good:    "0, 229, 160",
  bad:     "255, 76, 76",
  archaea: "245, 166, 35",
};

// Species metadata (role + display order)
const SPECIES_META: Array<{ id: string; name: string; instrument: string; role: "good" | "bad" | "archaea" }> = [
  { id: "f_prausnitzii",     name: "F. prausnitzii",     instrument: "First Violin",      role: "good" },
  { id: "b_longum",          name: "B. longum",           instrument: "Piano",             role: "good" },
  { id: "l_rhamnosus",       name: "L. rhamnosus",        instrument: "Acoustic Guitar",   role: "good" },
  { id: "a_muciniphila",     name: "A. muciniphila",      instrument: "Trumpet",           role: "good" },
  { id: "r_intestinalis",    name: "R. intestinalis",     instrument: "Accordion",         role: "good" },
  { id: "b_thetaiotaomicron",name: "B. thetaiotaomicron", instrument: "Cello",             role: "good" },
  { id: "r_bromii",          name: "R. bromii",           instrument: "Snare Drum",        role: "good" },
  { id: "e_hallii",          name: "E. hallii",           instrument: "Bass Guitar",       role: "good" },
  { id: "c_minuta",          name: "C. minuta",           instrument: "Viola",             role: "good" },
  { id: "c_difficile",       name: "C. difficile",        instrument: "Alarm Bell",        role: "bad" },
  { id: "h_pylori",          name: "H. pylori",           instrument: "Off-key Drone",     role: "bad" },
  { id: "f_nucleatum",       name: "F. nucleatum",        instrument: "Static Burst",      role: "bad" },
  { id: "d_piger",           name: "D. piger",            instrument: "Sulfur Tone",       role: "bad" },
  { id: "m_smithii",         name: "M. smithii",          instrument: "Pipe Organ",        role: "archaea" },
];

const EVENT_DEFS = [
  { type: "MEAL",       label: "Meal",       emoji: "🍽" },
  { type: "EXERCISE",   label: "Exercise",   emoji: "🏃" },
  { type: "PROBIOTIC",  label: "Probiotic",  emoji: "💊" },
  { type: "ANTIBIOTIC", label: "Antibiotic", emoji: "⚠" },
  { type: "STRESS",     label: "Stress",     emoji: "😤" },
  { type: "SLEEP",      label: "Sleep",      emoji: "💤" },
];

const HORIZON_OPTIONS = [
  { label: "6 h",  value: 6 * 3600 },
  { label: "12 h", value: 12 * 3600 },
  { label: "24 h", value: 24 * 3600 },
  { label: "48 h", value: 48 * 3600 },
  { label: "72 h", value: 72 * 3600 },
];

// Chart lines to display
const CHART_PARAMS = [
  { key: "diversity_index",    label: "Diversity",    rgb: "0, 229, 160" },
  { key: "inflammation_score", label: "Inflammation", rgb: "255, 76, 76" },
  { key: "motility_activity",  label: "Motility",     rgb: "91, 155, 213" },
  { key: "mucosal_integrity",  label: "Mucosal",      rgb: "245, 166, 35" },
];

// ---------------------------------------------------------------------------
// SVG chart helpers
// ---------------------------------------------------------------------------

const CW = 560;          // viewBox width
const CH = 120;          // viewBox height
const ML = 36;           // margin left (y-axis labels)
const MB = 24;           // margin bottom (x-axis labels)
const MT = 8;            // margin top
const MR = 8;            // margin right
const PW = CW - ML - MR; // plot width
const PH = CH - MT - MB; // plot height

function tx(t: number, horizon: number) {
  return ML + (t / horizon) * PW;
}
function ty(v: number) {
  return MT + (1 - Math.max(0, Math.min(1, v))) * PH;
}
function pathD(points: [number, number][]): string {
  return points.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
}

interface ChartProps {
  prediction: PredictResponse;
  horizon: number;
  events: Array<{ type: string; offset_seconds: number }>;
}

function ForecastChart({ prediction, horizon, events }: ChartProps) {
  const { t_steps } = prediction;

  // Y-axis gridlines
  const gridYs = [0, 0.25, 0.5, 0.75, 1.0];

  return (
    <svg
      viewBox={`0 0 ${CW} ${CH}`}
      className="w-full"
      style={{ height: 160 }}
      preserveAspectRatio="none"
    >
      {/* Gridlines */}
      {gridYs.map((v) => (
        <g key={v}>
          <line
            x1={ML} x2={CW - MR}
            y1={ty(v)} y2={ty(v)}
            stroke="rgba(255,255,255,0.05)" strokeWidth={1}
          />
          <text
            x={ML - 4} y={ty(v) + 3.5}
            textAnchor="end" fontSize={8}
            fill="rgba(232,237,242,0.25)"
            fontFamily="monospace"
          >
            {v.toFixed(1)}
          </text>
        </g>
      ))}

      {/* Confidence bands + lines */}
      {CHART_PARAMS.map(({ key, rgb }) => {
        const pred = prediction.predictions[key];
        if (!pred) return null;

        const upperPts = t_steps.map((t, i): [number, number] => [tx(t, horizon), ty(pred.upper[i])]);
        const lowerPts = t_steps.map((t, i): [number, number] => [tx(t, horizon), ty(pred.lower[i])]);
        const meanPts  = t_steps.map((t, i): [number, number] => [tx(t, horizon), ty(pred.mean[i])]);

        // Band polygon: upper L→R, lower R→L
        const bandPoints = [...upperPts, ...[...lowerPts].reverse()];
        const bandD = pathD(bandPoints) + " Z";

        return (
          <g key={key}>
            <path d={bandD} fill={`rgba(${rgb}, 0.10)`} />
            <polyline
              points={meanPts.map(([x, y]) => `${x},${y}`).join(" ")}
              fill="none"
              stroke={`rgb(${rgb})`}
              strokeWidth={1.5}
              strokeLinejoin="round"
            />
          </g>
        );
      })}

      {/* Event markers */}
      {events.map((ev, i) => {
        if (ev.offset_seconds < 0 || ev.offset_seconds > horizon) return null;
        const x = tx(ev.offset_seconds, horizon);
        const def = EVENT_DEFS.find((e) => e.type === ev.type);
        return (
          <g key={i}>
            <line x1={x} x2={x} y1={MT} y2={MT + PH}
              stroke="rgba(255,255,255,0.2)" strokeWidth={1} strokeDasharray="3,3" />
            <text x={x + 2} y={MT + 10} fontSize={8}
              fill="rgba(232,237,242,0.5)" fontFamily="monospace">
              {def?.emoji ?? ev.type.slice(0, 2)}
            </text>
          </g>
        );
      })}

      {/* X-axis labels */}
      {[0, 0.25, 0.5, 0.75, 1.0].map((frac) => {
        const t = frac * horizon;
        const hrs = t / 3600;
        return (
          <text
            key={frac}
            x={tx(t, horizon)} y={CH - 6}
            textAnchor="middle" fontSize={8}
            fill="rgba(232,237,242,0.3)"
            fontFamily="monospace"
          >
            {hrs < 1 ? "now" : `+${Math.round(hrs)}h`}
          </text>
        );
      })}
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Instrument timeline (piano roll)
// ---------------------------------------------------------------------------

function InstrumentTimeline({ trajectory, tSteps, horizon }: {
  trajectory: Record<string, number[]>;
  tSteps: number[];
  horizon: number;
}) {
  return (
    <div className="flex flex-col gap-0.5">
      {SPECIES_META.map((sp) => {
        const amps = trajectory[sp.id] ?? tSteps.map(() => 0);
        const rgb = ROLE_RGB[sp.role];

        // CSS gradient: one stop per step
        const stops = tSteps
          .map((t, i) => `rgba(${rgb}, ${amps[i].toFixed(3)}) ${((t / horizon) * 100).toFixed(1)}%`)
          .join(", ");

        const anyActive = amps.some((a) => a > 0.05);

        return (
          <div
            key={sp.id}
            className="flex items-center gap-2"
            style={{ opacity: anyActive ? 1 : 0.25 }}
          >
            {/* Species label */}
            <div className="flex-shrink-0 w-32">
              <p className="text-[9px] font-mono truncate" style={{ color: `rgba(${rgb}, 0.7)` }}>
                {sp.instrument}
              </p>
              <p className="text-[8px] italic truncate" style={{ color: "rgba(232,237,242,0.2)" }}>
                {sp.name}
              </p>
            </div>

            {/* Gradient track */}
            <div
              className="flex-1 h-4 rounded-sm"
              style={{
                background: anyActive
                  ? `linear-gradient(to right, ${stops})`
                  : "rgba(255,255,255,0.03)",
                boxShadow: anyActive ? `0 0 4px rgba(${rgb}, 0.15)` : "none",
              }}
            />
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface PredictionPanelProps {
  biomeState: BiomeState;
}

interface SelectedEvent {
  uid: string;
  type: string;
  offset_hours: number;
}

export default function PredictionPanel({ biomeState }: PredictionPanelProps) {
  const [horizon, setHorizon] = useState(24 * 3600);
  const [events, setEvents]   = useState<SelectedEvent[]>([]);
  const [prediction, setPrediction] = useState<PredictResponse | null>(null);
  const [loading, setLoading]    = useState(false);
  const [audioLoading, setAudioLoading] = useState(false);
  const [audioUrl, setAudioUrl]  = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const runForecast = useCallback(
    async (evts: SelectedEvent[], hrz: number) => {
      setLoading(true);
      setPrediction(null);
      try {
        const apiEvents: PredictEvent[] = evts.map((e) => ({
          type: e.type,
          offset_seconds: e.offset_hours * 3600,
        }));
        const result = await predictTrajectory(biomeState, apiEvents, hrz, 48);
        setPrediction(result);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    },
    [biomeState],
  );

  // Auto-run on mount and when events/horizon change (debounced)
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => runForecast(events, horizon), 400);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [events, horizon, runForecast]);

  const addEvent = (type: string) => {
    const defaultOffsets: Record<string, number> = {
      MEAL: 1, EXERCISE: 2, PROBIOTIC: 0.25, ANTIBIOTIC: 0.5, STRESS: 0.5, SLEEP: 6,
    };
    setEvents((prev) => [
      ...prev,
      { uid: Math.random().toString(36).slice(2), type, offset_hours: defaultOffsets[type] ?? 1 },
    ]);
  };

  const removeEvent = (uid: string) => setEvents((prev) => prev.filter((e) => e.uid !== uid));

  const updateOffset = (uid: string, hours: number) =>
    setEvents((prev) => prev.map((e) => e.uid === uid ? { ...e, offset_hours: hours } : e));

  const handleHearFuture = async () => {
    setAudioLoading(true);
    setAudioUrl(null);
    try {
      const apiEvents: PredictEvent[] = events.map((e) => ({
        type: e.type,
        offset_seconds: e.offset_hours * 3600,
      }));
      const result = await predictAudio(biomeState, apiEvents, horizon, 24);
      if (result.audio_url) setAudioUrl(getAudioUrl(result.audio_url));
    } catch (err) {
      console.error(err);
    } finally {
      setAudioLoading(false);
    }
  };

  const avgConfidence = prediction
    ? prediction.confidence.reduce((a, b) => a + b, 0) / prediction.confidence.length
    : 0;

  return (
    <div className="flex flex-col gap-5">

      {/* Horizon selector */}
      <div>
        <p className="font-mono text-[9px] uppercase tracking-[0.15em] mb-2"
           style={{ color: "rgba(232,237,242,0.28)" }}>
          Forecast window
        </p>
        <div className="flex gap-1.5">
          {HORIZON_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setHorizon(opt.value)}
              className="font-mono text-[10px] px-3 py-1.5 rounded transition-all"
              style={{
                background: horizon === opt.value ? "rgba(0,229,160,0.1)" : "rgba(255,255,255,0.03)",
                border: `1px solid ${horizon === opt.value ? "rgba(0,229,160,0.3)" : "rgba(255,255,255,0.06)"}`,
                color: horizon === opt.value ? "#00E5A0" : "rgba(232,237,242,0.35)",
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Event picker */}
      <div>
        <p className="font-mono text-[9px] uppercase tracking-[0.15em] mb-2"
           style={{ color: "rgba(232,237,242,0.28)" }}>
          Add lifestyle events
        </p>
        <div className="flex flex-wrap gap-1.5">
          {EVENT_DEFS.map((ev) => (
            <button
              key={ev.type}
              onClick={() => addEvent(ev.type)}
              className="font-mono text-[10px] px-2.5 py-1.5 rounded transition-all"
              style={{
                background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(255,255,255,0.07)",
                color: "rgba(232,237,242,0.5)",
              }}
            >
              {ev.emoji} {ev.label}
            </button>
          ))}
        </div>
      </div>

      {/* Selected events */}
      {events.length > 0 && (
        <div className="flex flex-col gap-1.5">
          {events.map((ev) => {
            const def = EVENT_DEFS.find((e) => e.type === ev.type)!;
            return (
              <div
                key={ev.uid}
                className="flex items-center gap-3 px-3 py-2 rounded"
                style={{ background: "rgba(0,229,160,0.04)", border: "1px solid rgba(0,229,160,0.12)" }}
              >
                <span className="text-[12px]">{def.emoji}</span>
                <span className="font-mono text-[11px] flex-1" style={{ color: "#00E5A0" }}>{def.label}</span>
                <span className="font-mono text-[10px]" style={{ color: "rgba(232,237,242,0.3)" }}>+</span>
                <input
                  type="number"
                  min="0"
                  max="72"
                  step="0.5"
                  value={ev.offset_hours}
                  onChange={(e) => updateOffset(ev.uid, parseFloat(e.target.value) || 0)}
                  className="w-14 bg-transparent font-mono text-[11px] text-center rounded px-1 py-0.5"
                  style={{
                    border: "1px solid rgba(255,255,255,0.1)",
                    color: "rgba(232,237,242,0.7)",
                    outline: "none",
                  }}
                />
                <span className="font-mono text-[10px]" style={{ color: "rgba(232,237,242,0.3)" }}>h</span>
                <button
                  onClick={() => removeEvent(ev.uid)}
                  className="font-mono text-[11px] px-1.5 transition-colors"
                  style={{ color: "rgba(255,255,255,0.2)" }}
                >
                  ×
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* Chart */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <p className="font-mono text-[9px] uppercase tracking-[0.15em]"
             style={{ color: "rgba(232,237,242,0.28)" }}>
            Trajectory
          </p>
          <div className="flex gap-3">
            {CHART_PARAMS.map(({ label, rgb }) => (
              <span key={label} className="flex items-center gap-1">
                <span className="w-5 h-[2px] inline-block rounded" style={{ background: `rgb(${rgb})` }} />
                <span className="font-mono text-[8px]" style={{ color: `rgba(${rgb}, 0.7)` }}>{label}</span>
              </span>
            ))}
          </div>
        </div>

        <div
          className="rounded overflow-hidden"
          style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)" }}
        >
          {loading ? (
            <div className="flex items-center justify-center h-40">
              <span className="font-mono text-[11px] animate-pulse" style={{ color: "rgba(232,237,242,0.3)" }}>
                Computing forecast...
              </span>
            </div>
          ) : prediction ? (
            <ForecastChart
              prediction={prediction}
              horizon={horizon}
              events={events.map((e) => ({ type: e.type, offset_seconds: e.offset_hours * 3600 }))}
            />
          ) : null}
        </div>
      </div>

      {/* Instrument timeline */}
      {prediction && (
        <div>
          <p className="font-mono text-[9px] uppercase tracking-[0.15em] mb-2.5"
             style={{ color: "rgba(232,237,242,0.28)" }}>
            Instrument activity over time
          </p>
          <InstrumentTimeline
            trajectory={prediction.instrument_trajectory}
            tSteps={prediction.t_steps}
            horizon={horizon}
          />
        </div>
      )}

      {/* Footer row */}
      <div
        className="flex items-center justify-between gap-3 pt-3"
        style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}
      >
        {/* Confidence */}
        {prediction && (
          <div>
            <p className="font-mono text-[9px] uppercase tracking-[0.15em] mb-1"
               style={{ color: "rgba(232,237,242,0.28)" }}>
              Confidence
            </p>
            <div className="flex items-center gap-2">
              <div className="w-20 h-[3px] rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.07)" }}>
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{ width: `${avgConfidence * 100}%`, background: "#00E5A0" }}
                />
              </div>
              <span className="font-mono text-[11px]" style={{ color: "rgba(232,237,242,0.4)" }}>
                {(avgConfidence * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        )}

        {/* Hear the future */}
        <div className="flex flex-col items-end gap-2">
          <button
            onClick={handleHearFuture}
            disabled={audioLoading}
            className="font-mono text-[11px] px-4 py-2 rounded transition-all disabled:opacity-40"
            style={{
              background: "rgba(0,229,160,0.1)",
              border: "1px solid rgba(0,229,160,0.25)",
              color: "#00E5A0",
            }}
          >
            {audioLoading ? "Composing..." : "Hear the future →"}
          </button>
          {audioUrl && (
            <audio
              src={audioUrl}
              controls
              className="h-8 w-52"
              style={{ filter: "invert(1) sepia(1) saturate(0) hue-rotate(0deg) brightness(0.6)" }}
            />
          )}
        </div>
      </div>
    </div>
  );
}
