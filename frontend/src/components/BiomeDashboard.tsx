"use client";

import { useEffect, useState } from "react";
import type { BiomeState } from "@/lib/api";

interface BiomeDashboardProps {
  biomeState: BiomeState;
  onAdjust?: (adjusted: BiomeState) => void;
}

interface GaugeConfig {
  key: keyof BiomeState;
  label: string;
  healthyDirection: "high" | "low";
  description: string;
}

const GAUGES: GaugeConfig[] = [
  { key: "diversity_index", label: "Diversity", healthyDirection: "high", description: "Microbial species richness" },
  { key: "inflammation_score", label: "Inflammation", healthyDirection: "low", description: "Tissue inflammatory state" },
  { key: "firmicutes_dominance", label: "Firmicutes", healthyDirection: "high", description: "Foundation phylum presence" },
  { key: "bacteroidetes_dominance", label: "Bacteroidetes", healthyDirection: "high", description: "Metabolic workhorse presence" },
  { key: "proteobacteria_bloom", label: "Proteobacteria", healthyDirection: "low", description: "Pathogenic bloom indicator" },
  { key: "motility_activity", label: "Motility", healthyDirection: "high", description: "Gut movement & peristalsis" },
  { key: "mucosal_integrity", label: "Mucosal Integrity", healthyDirection: "high", description: "Barrier tissue health" },
  { key: "metabolic_energy", label: "Metabolic Energy", healthyDirection: "high", description: "Inferred metabolic activity" },
];

function getGaugeColor(value: number, healthyDirection: "high" | "low"): string {
  const health = healthyDirection === "high" ? value : 1 - value;
  if (health > 0.6) return "0, 240, 255";     // teal
  if (health > 0.3) return "255, 200, 50";     // amber
  return "255, 45, 45";                         // red
}

export default function BiomeDashboard({ biomeState, onAdjust }: BiomeDashboardProps) {
  const [animated, setAnimated] = useState(false);
  const [localState, setLocalState] = useState(biomeState);

  useEffect(() => {
    setLocalState(biomeState);
    // Trigger staggered animation on mount
    const timer = setTimeout(() => setAnimated(true), 50);
    return () => clearTimeout(timer);
  }, [biomeState]);

  const handleSliderChange = (key: keyof BiomeState, value: number) => {
    const updated = { ...localState, [key]: value };
    setLocalState(updated);
    onAdjust?.(updated);
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-5">
      {GAUGES.map(({ key, label, healthyDirection, description }, index) => {
        const value = localState[key];
        const rgb = getGaugeColor(value, healthyDirection);
        const color = `rgb(${rgb})`;

        return (
          <div
            key={key}
            className="group"
            style={{
              opacity: animated ? 1 : 0,
              transform: animated ? "translateY(0)" : "translateY(8px)",
              transition: `opacity 0.6s ease ${index * 0.06}s, transform 0.6s ease ${index * 0.06}s`,
            }}
          >
            {/* Label row */}
            <div className="flex items-baseline justify-between mb-1">
              <div className="flex items-center gap-2">
                {/* Status dot */}
                <div
                  className="w-1.5 h-1.5 rounded-full transition-colors duration-700"
                  style={{
                    backgroundColor: color,
                    boxShadow: `0 0 6px rgba(${rgb}, 0.5)`,
                  }}
                />
                <span className="text-[11px] text-muted uppercase tracking-wider">
                  {label}
                </span>
              </div>
              <span
                className="font-mono text-xs tabular-nums transition-colors duration-700"
                style={{ color }}
              >
                {value.toFixed(2)}
              </span>
            </div>

            {/* Gauge bar */}
            <div className="relative h-[3px] bg-surface-light/60 rounded-full overflow-hidden">
              {/* Background tick marks */}
              <div className="absolute inset-0 flex">
                {[...Array(10)].map((_, i) => (
                  <div
                    key={i}
                    className="flex-1 border-r border-background/30 last:border-r-0"
                  />
                ))}
              </div>
              {/* Fill bar */}
              <div
                className="absolute inset-y-0 left-0 rounded-full"
                style={{
                  width: animated ? `${value * 100}%` : "0%",
                  backgroundColor: color,
                  boxShadow: `0 0 12px rgba(${rgb}, 0.3), 0 0 4px rgba(${rgb}, 0.2)`,
                  transition: `width 1.2s cubic-bezier(0.16, 1, 0.3, 1) ${index * 0.06}s, background-color 0.7s ease, box-shadow 0.7s ease`,
                }}
              />
            </div>

            {/* Slider (if adjustable) */}
            {onAdjust && (
              <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={value}
                onChange={(e) => handleSliderChange(key, parseFloat(e.target.value))}
                className="
                  w-full h-1 mt-2 appearance-none bg-transparent cursor-pointer
                  opacity-0 group-hover:opacity-100 transition-opacity duration-300
                  [&::-webkit-slider-thumb]:appearance-none
                  [&::-webkit-slider-thumb]:w-2.5 [&::-webkit-slider-thumb]:h-2.5
                  [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-accent
                  [&::-webkit-slider-thumb]:shadow-[0_0_6px_rgba(0,240,255,0.5)]
                  [&::-webkit-slider-runnable-track]:h-[1px]
                  [&::-webkit-slider-runnable-track]:bg-surface-light
                  [&::-webkit-slider-runnable-track]:rounded-full
                "
              />
            )}

            {/* Tooltip description */}
            <p className="text-[9px] text-muted/0 group-hover:text-muted/60 transition-colors duration-300 mt-0.5 font-mono">
              {description}
            </p>
          </div>
        );
      })}
    </div>
  );
}
