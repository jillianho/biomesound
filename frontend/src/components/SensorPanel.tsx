"use client";

import { useState, useCallback, useRef } from "react";
import { sendSensorReading, getAudioUrl, type BiomeState, type SensorResponse } from "@/lib/api";

interface SensorPanelProps {
  onResult: (biomeState: BiomeState, audioUrl: string, meta: { state: string; mood: string; score: number }) => void;
}

const PRESETS = [
  { name: "healthy",    label: "Healthy",     ph: 6.4, h2: 6.0, ch4: 0.8, temp: 37.0 },
  { name: "peak",       label: "Peak",        ph: 6.2, h2: 12.0, ch4: 1.2, temp: 37.0 },
  { name: "sugar",      label: "Sugar spike", ph: 7.8, h2: 0.5, ch4: 0.3, temp: 37.5 },
  { name: "inflamed",   label: "Inflamed",    ph: 8.1, h2: 0.3, ch4: 0.2, temp: 38.3 },
  { name: "methanogen", label: "Methanogen",  ph: 6.8, h2: 1.0, ch4: 7.5, temp: 36.9 },
  { name: "fasted",     label: "Fasted",      ph: 7.0, h2: 0.8, ch4: 0.5, temp: 37.0 },
];

const STATE_COLORS: Record<string, string> = {
  peak_diversity: "0, 229, 160",
  healthy:        "0, 229, 160",
  fasted:         "91, 155, 213",
  methanogen:     "245, 166, 35",
  dysbiosis:      "255, 140, 66",
  inflamed:       "255, 76, 76",
};

export default function SensorPanel({ onResult }: SensorPanelProps) {
  const [ph,   setPh]   = useState(6.5);
  const [h2,   setH2]   = useState(4.0);
  const [ch4,  setCh4]  = useState(1.0);
  const [temp, setTemp] = useState(37.0);

  const [loading,  setLoading]  = useState(false);
  const [result,   setResult]   = useState<SensorResponse | null>(null);
  const [error,    setError]    = useState<string | null>(null);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const submit = useCallback(async (vals: { ph: number; h2: number; ch4: number; temp: number }) => {
    setLoading(true);
    setError(null);
    try {
      const res = await sendSensorReading({
        ph: vals.ph,
        h2_ppm: vals.h2,
        ch4_ppm: vals.ch4,
        temp_c: vals.temp,
      });
      setResult(res);
      onResult(res.biome, getAudioUrl(res.audio_url), {
        state: res.state,
        mood: res.mood,
        score: res.score,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sensor error");
    } finally {
      setLoading(false);
    }
  }, [onResult]);

  const handleSlider = (setter: (v: number) => void, value: number, allVals: object) => {
    setter(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => submit({ ph, h2, ch4, temp, ...allVals }), 500);
  };

  const applyPreset = (p: typeof PRESETS[0]) => {
    setPh(p.ph); setH2(p.h2); setCh4(p.ch4); setTemp(p.temp);
    submit({ ph: p.ph, h2: p.h2, ch4: p.ch4, temp: p.temp });
  };

  const rgb = result ? (STATE_COLORS[result.state] || "0,229,160") : "100,100,100";
  const score = result?.score ?? null;

  return (
    <div className="flex flex-col gap-5">

      {/* Score + mood display */}
      {result && (
        <div
          className="flex items-center justify-between px-4 py-3 rounded border"
          style={{
            borderColor: `rgba(${rgb}, 0.3)`,
            background: `rgba(${rgb}, 0.05)`,
            transition: "all 0.6s ease",
          }}
        >
          <div>
            <p className="font-mono text-[10px] uppercase tracking-widest text-muted/60 mb-0.5">
              Gut score
            </p>
            <p
              className="font-mono text-3xl font-bold tabular-nums"
              style={{ color: `rgb(${rgb})` }}
            >
              {score}
            </p>
          </div>
          <div className="text-right">
            <p className="font-mono text-[10px] uppercase tracking-widest text-muted/60 mb-0.5">
              Music mood
            </p>
            <p className="text-sm font-light" style={{ color: `rgb(${rgb})` }}>
              {result.mood}
            </p>
            <p className="font-mono text-[9px] text-muted/40 uppercase tracking-wider mt-0.5">
              {result.state.replace(/_/g, " ")}
            </p>
          </div>
        </div>
      )}

      {/* Preset buttons */}
      <div>
        <p className="font-mono text-[10px] uppercase tracking-widest text-muted/40 mb-2">
          Presets
        </p>
        <div className="flex flex-wrap gap-2">
          {PRESETS.map((p) => (
            <button
              key={p.name}
              onClick={() => applyPreset(p)}
              className="
                font-mono text-[10px] uppercase tracking-wider
                px-3 py-1.5 rounded border
                border-surface-light text-muted
                hover:border-accent/30 hover:text-accent
                transition-all duration-200
              "
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Sliders */}
      <div className="flex flex-col gap-4">
        <SensorSlider
          label="pH"
          value={ph} min={4} max={9} step={0.1}
          onChange={(v) => handleSlider(setPh, v, { ph: v })}
          color={ph > 7.2 ? "255,76,76" : ph < 6.0 ? "245,166,35" : "0,229,160"}
        />
        <SensorSlider
          label="H₂ (ppm)"
          value={h2} min={0} max={20} step={0.5}
          onChange={(v) => handleSlider(setH2, v, { h2: v })}
          color="0,229,160"
        />
        <SensorSlider
          label="CH₄ (ppm)"
          value={ch4} min={0} max={10} step={0.5}
          onChange={(v) => handleSlider(setCh4, v, { ch4: v })}
          color="245,166,35"
        />
        <SensorSlider
          label="Temp (°C)"
          value={temp} min={35} max={39} step={0.1}
          onChange={(v) => handleSlider(setTemp, v, { temp: v })}
          color={temp > 37.8 ? "255,76,76" : "91,155,213"}
        />
      </div>

      {/* Status */}
      <div className="font-mono text-[10px] text-muted/40 min-h-4">
        {loading && (
          <span className="animate-pulse">generating sound...</span>
        )}
        {error && (
          <span className="text-accent-red">{error}</span>
        )}
        {!loading && !error && result && (
          <span>
            diversity {result.biome.diversity_index.toFixed(2)} · 
            inflammation {result.biome.inflammation_score.toFixed(2)} · 
            motility {result.biome.motility_activity.toFixed(2)}
          </span>
        )}
      </div>
    </div>
  );
}


// ── sub-component: single slider row ─────────────────────────────────────

function SensorSlider({
  label, value, min, max, step, onChange, color,
}: {
  label: string;
  value: number;
  min: number; max: number; step: number;
  onChange: (v: number) => void;
  color: string;
}) {
  return (
    <div>
      <div className="flex justify-between mb-1">
        <span className="font-mono text-[10px] uppercase tracking-wider text-muted/60">
          {label}
        </span>
        <span
          className="font-mono text-[10px] tabular-nums"
          style={{ color: `rgb(${color})` }}
        >
          {value.toFixed(1)}
        </span>
      </div>
      <div className="relative h-[3px] bg-surface-light/60 rounded-full">
        <div
          className="absolute inset-y-0 left-0 rounded-full transition-all duration-300"
          style={{
            width: `${((value - min) / (max - min)) * 100}%`,
            background: `rgb(${color})`,
            boxShadow: `0 0 8px rgba(${color}, 0.4)`,
          }}
        />
      </div>
      <input
        type="range"
        min={min} max={max} step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="
          w-full h-1 mt-1 appearance-none bg-transparent cursor-pointer
          [&::-webkit-slider-thumb]:appearance-none
          [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3
          [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-accent
          [&::-webkit-slider-thumb]:shadow-[0_0_6px_rgba(0,240,255,0.5)]
          [&::-webkit-slider-runnable-track]:h-[1px]
          [&::-webkit-slider-runnable-track]:bg-surface-light
          [&::-webkit-slider-runnable-track]:rounded-full
        "
      />
    </div>
  );
}
