"use client";

import { useEffect, useState } from "react";

interface ProcessingAnimationProps {
  phase: "extracting" | "inferring" | "composing";
}

const PHASE_LABELS = {
  extracting: "Extracting visual features",
  inferring: "Inferring biome state",
  composing: "Composing audio",
};

const PHASE_INDEX = {
  extracting: 0,
  inferring: 1,
  composing: 2,
};

export default function ProcessingAnimation({
  phase,
}: ProcessingAnimationProps) {
  const [dots, setDots] = useState("");

  useEffect(() => {
    const interval = setInterval(() => {
      setDots((d) => (d.length >= 3 ? "" : d + "."));
    }, 500);
    return () => clearInterval(interval);
  }, []);

  const currentIndex = PHASE_INDEX[phase];

  return (
    <div className="flex flex-col items-center gap-12">
      {/* Pulsing rings */}
      <div className="relative w-32 h-32 flex items-center justify-center">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="absolute inset-0 rounded-full border border-accent/20"
            style={{
              animation: `pulse-ring 3s ease-out infinite`,
              animationDelay: `${i * 1}s`,
              transform: `scale(${0.3 + i * 0.2})`,
            }}
          />
        ))}
        <div
          className="w-3 h-3 rounded-full bg-accent"
          style={{ animation: "pulse-dot 2s ease-in-out infinite" }}
        />
      </div>

      {/* Phase indicators */}
      <div className="flex flex-col gap-4">
        {(["extracting", "inferring", "composing"] as const).map((p, i) => (
          <div
            key={p}
            className={`
              flex items-center gap-3 font-mono text-sm
              transition-all duration-700
              ${
                i < currentIndex
                  ? "text-accent/40"
                  : i === currentIndex
                  ? "text-accent"
                  : "text-muted/30"
              }
            `}
          >
            <div
              className={`
                w-1.5 h-1.5 rounded-full transition-all duration-500
                ${
                  i < currentIndex
                    ? "bg-accent/40"
                    : i === currentIndex
                    ? "bg-accent shadow-[0_0_8px_rgba(0,240,255,0.5)]"
                    : "bg-muted/20"
                }
              `}
            />
            <span>
              {PHASE_LABELS[p]}
              {i === currentIndex ? dots : i < currentIndex ? " ✓" : ""}
            </span>
          </div>
        ))}
      </div>

      <style jsx>{`
        @keyframes pulse-ring {
          0% {
            opacity: 0.3;
            transform: scale(0.8);
          }
          50% {
            opacity: 0.1;
          }
          100% {
            opacity: 0;
            transform: scale(1.6);
          }
        }
        @keyframes pulse-dot {
          0%,
          100% {
            opacity: 0.6;
            transform: scale(1);
          }
          50% {
            opacity: 1;
            transform: scale(1.3);
          }
        }
      `}</style>
    </div>
  );
}
