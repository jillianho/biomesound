"use client";

import { useState, useRef } from "react";
import { runComprehensive, getAudioUrl, type ComprehensiveResponse, type BiomeState } from "@/lib/api";

const CHANNEL_RGB: Record<string, string> = {
  visual:     "138, 180, 248",
  ph_temp:    "0, 229, 160",
  breath_gas: "245, 166, 35",
};

const CHANNEL_LABELS: Record<string, string> = {
  visual:     "Visual Analysis",
  ph_temp:    "pH + Temp Capsule",
  breath_gas: "Breath Gas Analyzer",
};

interface ComprehensivePanelProps {
  genre: string;
  onResult: (
    biomeState: BiomeState,
    audioUrl: string,
    meta: { state: string; mood: string; score: number },
    comprehensive: ComprehensiveResponse,
  ) => void;
}

export default function ComprehensivePanel({ genre, onResult }: ComprehensivePanelProps) {
  const [visualOn, setVisualOn]   = useState(true);
  const [phTempOn, setPhTempOn]   = useState(false);
  const [breathOn, setBreathOn]   = useState(false);

  const [file, setFile]     = useState<File | null>(null);
  const fileRef             = useRef<HTMLInputElement>(null);

  const [ph, setPh]         = useState(6.5);
  const [tempC, setTempC]   = useState(37.0);
  const [h2, setH2]         = useState(4.0);
  const [ch4, setCh4]       = useState(1.0);

  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState<string | null>(null);

  const activeCount = [visualOn && file, phTempOn, breathOn].filter(Boolean).length;
  const canSubmit   = activeCount > 0 && !loading;

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    try {
      const p: Parameters<typeof runComprehensive>[0] = { genre };
      if (visualOn && file) p.file = file;
      if (phTempOn) { p.ph = ph; p.temp_c = tempC; }
      if (breathOn) { p.h2_ppm = h2; p.ch4_ppm = ch4; }

      const res = await runComprehensive(p);
      onResult(
        res.fused_biome_state,
        getAudioUrl(res.audio_url),
        { state: res.state, mood: res.mood, score: res.gut_score },
        res,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-4 w-full">

      {/* ── Channel 1: Visual ── */}
      <ChannelCard channel="visual" enabled={visualOn} onToggle={setVisualOn}>
        <div
          className="border border-dashed rounded px-4 py-4 text-center cursor-pointer transition-all"
          style={{
            borderColor: file ? "rgba(138,180,248,0.4)" : "rgba(255,255,255,0.1)",
            background: file ? "rgba(138,180,248,0.04)" : "transparent",
            opacity: visualOn ? 1 : 0.3,
            pointerEvents: visualOn ? "auto" : "none",
          }}
          onClick={() => fileRef.current?.click()}
          onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) setFile(f); }}
          onDragOver={(e) => e.preventDefault()}
        >
          <input
            ref={fileRef}
            type="file"
            accept="image/*,video/*"
            className="hidden"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) setFile(f); }}
          />
          {file ? (
            <div className="flex items-center justify-center gap-2">
              <span className="font-mono text-[11px]" style={{ color: "rgb(138,180,248)" }}>
                {file.name}
              </span>
              <button
                onClick={(e) => { e.stopPropagation(); setFile(null); }}
                className="font-mono text-[9px] text-muted/40 hover:text-muted/80"
              >
                remove
              </button>
            </div>
          ) : (
            <p className="font-mono text-[10px]" style={{ color: "rgba(232,237,242,0.3)" }}>
              Drop image/video or click to upload
            </p>
          )}
        </div>
      </ChannelCard>

      {/* ── Channel 2: pH + Temperature ── */}
      <ChannelCard channel="ph_temp" enabled={phTempOn} onToggle={setPhTempOn}>
        <div className="flex flex-col gap-3" style={{ opacity: phTempOn ? 1 : 0.3, pointerEvents: phTempOn ? "auto" : "none" }}>
          <MiniSlider label="pH" value={ph} min={4} max={9} step={0.1} onChange={setPh}
            color={ph > 7.2 ? "255,76,76" : "0,229,160"} />
          <MiniSlider label="Temp (°C)" value={tempC} min={35} max={39} step={0.1} onChange={setTempC}
            color={tempC > 37.8 ? "255,76,76" : "91,155,213"} />
        </div>
      </ChannelCard>

      {/* ── Channel 3: Breath Gas ── */}
      <ChannelCard channel="breath_gas" enabled={breathOn} onToggle={setBreathOn}>
        <div className="flex flex-col gap-3" style={{ opacity: breathOn ? 1 : 0.3, pointerEvents: breathOn ? "auto" : "none" }}>
          <MiniSlider label="H₂ (ppm)" value={h2} min={0} max={20} step={0.5} onChange={setH2}
            color="0,229,160" />
          <MiniSlider label="CH₄ (ppm)" value={ch4} min={0} max={10} step={0.5} onChange={setCh4}
            color="245,166,35" />
        </div>
      </ChannelCard>

      {/* ── Submit ── */}
      <button
        onClick={handleSubmit}
        disabled={!canSubmit}
        className="font-mono text-[11px] uppercase tracking-widest py-3 rounded border transition-all"
        style={{
          borderColor: canSubmit ? "rgba(0,229,160,0.4)" : "rgba(255,255,255,0.07)",
          color:       canSubmit ? "#00E5A0" : "rgba(232,237,242,0.2)",
          background:  canSubmit ? "rgba(0,229,160,0.06)" : "transparent",
        }}
      >
        {loading ? (
          <span className="animate-pulse">Analyzing {activeCount} channel{activeCount !== 1 ? "s" : ""}...</span>
        ) : (
          `Analyze${activeCount > 0 ? ` (${activeCount} channel${activeCount !== 1 ? "s" : ""})` : ""}`
        )}
      </button>

      {error && (
        <p className="font-mono text-[10px] text-center" style={{ color: "rgb(255,76,76)" }}>{error}</p>
      )}
    </div>
  );
}


/* ── Sub-components ──────────────────────────────────────────────────────── */

function ChannelCard({
  channel, enabled, onToggle, children,
}: {
  channel: string;
  enabled: boolean;
  onToggle: (v: boolean) => void;
  children: React.ReactNode;
}) {
  const rgb   = CHANNEL_RGB[channel] || "100,100,100";
  const label = CHANNEL_LABELS[channel] || channel;

  return (
    <div
      className="rounded border px-4 py-3 transition-all"
      style={{
        borderColor: enabled ? `rgba(${rgb}, 0.25)` : "rgba(255,255,255,0.06)",
        background:  enabled ? `rgba(${rgb}, 0.03)` : "transparent",
      }}
    >
      <div className="flex items-center justify-between mb-3">
        <span
          className="font-mono text-[10px] uppercase tracking-[0.12em]"
          style={{ color: enabled ? `rgb(${rgb})` : "rgba(232,237,242,0.3)" }}
        >
          {label}
        </span>
        <button
          onClick={() => onToggle(!enabled)}
          className="font-mono text-[9px] px-2 py-0.5 rounded transition-all"
          style={{
            background: enabled ? `rgba(${rgb}, 0.15)` : "rgba(255,255,255,0.04)",
            color:      enabled ? `rgb(${rgb})` : "rgba(232,237,242,0.3)",
          }}
        >
          {enabled ? "ON" : "OFF"}
        </button>
      </div>
      {children}
    </div>
  );
}


function MiniSlider({
  label, value, min, max, step, onChange, color,
}: {
  label: string; value: number; min: number; max: number; step: number;
  onChange: (v: number) => void; color: string;
}) {
  return (
    <div>
      <div className="flex justify-between mb-0.5">
        <span className="font-mono text-[9px] uppercase tracking-wider" style={{ color: "rgba(232,237,242,0.4)" }}>
          {label}
        </span>
        <span className="font-mono text-[9px] tabular-nums" style={{ color: `rgb(${color})` }}>
          {value.toFixed(1)}
        </span>
      </div>
      <input
        type="range"
        min={min} max={max} step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="
          w-full h-1 appearance-none bg-transparent cursor-pointer
          [&::-webkit-slider-thumb]:appearance-none
          [&::-webkit-slider-thumb]:w-2.5 [&::-webkit-slider-thumb]:h-2.5
          [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-accent
          [&::-webkit-slider-runnable-track]:h-[2px]
          [&::-webkit-slider-runnable-track]:bg-surface-light
          [&::-webkit-slider-runnable-track]:rounded-full
        "
      />
    </div>
  );
}
