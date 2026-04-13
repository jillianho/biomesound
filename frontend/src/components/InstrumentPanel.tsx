"use client";

import { useState, useEffect } from "react";
import { getInstruments, type BiomeState, type InstrumentInfo } from "@/lib/api";

const ROLE_RGB: Record<string, string> = {
  good:    "0, 229, 160",
  bad:     "255, 76, 76",
  archaea: "245, 166, 35",
};

const ROLE_LABEL: Record<string, string> = {
  good:    "Good bacteria",
  bad:     "Pathogenic",
  archaea: "Archaea",
};

const OSC_LABELS: Record<string, string> = {
  sine:     "sine",
  triangle: "tri",
  sawtooth: "saw",
  square:   "sqr",
  noise:    "noise",
};

interface InstrumentPanelProps {
  biomeState: BiomeState;
  genre?: string;
}

export default function InstrumentPanel({ biomeState, genre = "classical" }: InstrumentPanelProps) {
  const [data, setData] = useState<{
    instruments: InstrumentInfo[];
    active_count: number;
    tempo_bpm: number;
    harmonic_richness: number;
    inflammation_detune: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getInstruments(biomeState, genre)
      .then((d) => { if (!cancelled) setData(d); })
      .catch(console.error)
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [biomeState, genre]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-28">
        <span className="font-mono text-[11px] animate-pulse" style={{ color: "rgba(232,237,242,0.3)" }}>
          Loading instruments...
        </span>
      </div>
    );
  }

  if (!data) return null;

  const byRole = {
    good:    data.instruments.filter((i) => i.role === "good"),
    bad:     data.instruments.filter((i) => i.role === "bad"),
    archaea: data.instruments.filter((i) => i.role === "archaea"),
  };

  return (
    <div className="flex flex-col gap-5">

      {/* Synthesis stats */}
      <div className="grid grid-cols-3 gap-px" style={{ background: "rgba(255,255,255,0.07)" }}>
        {[
          { label: "Tempo",           value: `${Math.round(data.tempo_bpm)} BPM` },
          { label: "Harmonic richness", value: `${(data.harmonic_richness * 100).toFixed(0)}%` },
          { label: "Active voices",   value: `${data.active_count} / ${data.instruments.length}` },
        ].map(({ label, value }) => (
          <div key={label} className="px-3 py-2.5" style={{ background: "#080C0F" }}>
            <p className="font-mono text-[9px] uppercase tracking-[0.15em] mb-1"
               style={{ color: "rgba(232,237,242,0.28)" }}>
              {label}
            </p>
            <p className="font-mono text-[14px]" style={{ color: "#00E5A0" }}>{value}</p>
          </div>
        ))}
      </div>

      {/* Instrument rows per role */}
      {(["good", "bad", "archaea"] as const).map((role) => (
        <div key={role}>
          <p
            className="font-mono text-[9px] uppercase tracking-[0.15em] mb-2"
            style={{ color: `rgba(${ROLE_RGB[role]}, 0.45)` }}
          >
            {ROLE_LABEL[role]}
          </p>
          <div className="flex flex-col gap-1.5">
            {byRole[role].map((inst, i) => (
              <InstrumentRow key={inst.id} inst={inst} role={role} index={i} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function InstrumentRow({
  inst,
  role,
  index,
}: {
  inst: InstrumentInfo;
  role: string;
  index: number;
}) {
  const rgb = ROLE_RGB[role];

  return (
    <div
      className="flex items-center gap-3 px-3 py-2 rounded transition-all duration-500"
      style={{
        background: inst.active ? `rgba(${rgb}, 0.06)` : "rgba(255,255,255,0.015)",
        border: `1px solid ${inst.active ? `rgba(${rgb}, 0.18)` : "rgba(255,255,255,0.04)"}`,
        opacity: inst.active ? 1 : 0.32,
        transform: inst.active ? "none" : "none",
        animationDelay: `${index * 40}ms`,
      }}
    >
      {/* Oscillator badge */}
      <span
        className="font-mono text-[9px] px-1.5 py-0.5 rounded flex-shrink-0"
        style={{
          background: `rgba(${rgb}, 0.1)`,
          color: `rgba(${rgb}, 0.7)`,
          minWidth: 30,
          textAlign: "center",
        }}
      >
        {OSC_LABELS[inst.oscillator] ?? inst.oscillator}
      </span>

      {/* Names */}
      <div className="flex-1 min-w-0">
        <p
          className="text-[12px] font-medium leading-none truncate"
          style={{ color: inst.active ? `rgb(${rgb})` : "rgba(232,237,242,0.28)" }}
        >
          {inst.instrument}
        </p>
        <p className="font-mono text-[10px] mt-0.5 italic truncate"
           style={{ color: "rgba(232,237,242,0.22)" }}>
          {inst.name}
        </p>
      </div>

      {/* Rhythm tags */}
      {(inst.percussive || inst.sporadic) && (
        <span
          className="font-mono text-[8px] px-1.5 py-0.5 rounded flex-shrink-0"
          style={{ background: "rgba(255,255,255,0.04)", color: `rgba(${rgb}, 0.4)` }}
        >
          {inst.percussive ? "rhythm" : "burst"}
        </span>
      )}

      {/* Amplitude bar */}
      <div className="flex flex-col gap-0.5 flex-shrink-0 w-20">
        <div className="h-[3px] rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.06)" }}>
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{
              width: `${inst.amplitude * 100}%`,
              background: `rgb(${rgb})`,
              boxShadow: inst.active ? `0 0 5px rgba(${rgb}, 0.45)` : "none",
            }}
          />
        </div>
        <p className="font-mono text-[8px] text-right" style={{ color: "rgba(232,237,242,0.18)" }}>
          {inst.freq_base >= 1000
            ? `${(inst.freq_base / 1000).toFixed(1)}kHz`
            : `${Math.round(inst.freq_base)}Hz`}
        </p>
      </div>
    </div>
  );
}
