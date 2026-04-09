"use client";

import { useEffect, useRef } from "react";
import type { BiomeState } from "@/lib/api";

const STATE_COLORS: Record<string, string> = {
  peak_diversity: "#00F0C8",
  healthy: "#00F0C8",
  fasted: "#5B9BD5",
  methanogen: "#F5A623",
  dysbiosis: "#FF8C42",
  inflamed: "#FF4C4C",
};

interface WaveformAnimationProps {
  biomeState: BiomeState;
  gutState: string;
}

export default function WaveformAnimation({ biomeState, gutState }: WaveformAnimationProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const phaseRef = useRef(0);
  const animRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    function draw() {
      const c = canvasRef.current;
      if (!c) return;
      const context = c.getContext("2d");
      if (!context) return;

      // Match canvas resolution to display size
      const rect = c.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      c.width = rect.width * dpr;
      c.height = rect.height * dpr;
      context.scale(dpr, dpr);
      const w = rect.width;
      const h = rect.height;

      context.clearRect(0, 0, w, h);

      const color = STATE_COLORS[gutState] || "#00F0C8";
      const complexity = biomeState.diversity_index;
      const inflammation = biomeState.inflammation_score;
      const amplitude = h * 0.28 * (0.3 + complexity * 0.7);
      const freq = 0.012 + complexity * 0.018;
      const chaos = inflammation * 0.6;

      // Primary wave
      context.strokeStyle = color;
      context.lineWidth = 1.5;
      context.globalAlpha = 0.85;
      context.beginPath();

      for (let x = 0; x < w; x++) {
        const t = x * freq + phaseRef.current;
        let y = Math.sin(t) * amplitude;
        if (complexity > 0.4) y += Math.sin(t * 2.1 + 0.5) * amplitude * 0.4 * complexity;
        if (complexity > 0.65) y += Math.sin(t * 3.7 + 1.2) * amplitude * 0.25 * complexity;
        if (chaos > 0.2) y += (Math.random() - 0.5) * amplitude * chaos * 0.5;
        const cy = h / 2 + y;
        x === 0 ? context.moveTo(x, cy) : context.lineTo(x, cy);
      }
      context.stroke();

      // Subtle second wave for healthy states
      if (complexity > 0.55) {
        context.globalAlpha = 0.25;
        context.strokeStyle = color;
        context.beginPath();
        for (let x = 0; x < w; x++) {
          const t = x * freq * 0.7 + phaseRef.current * 0.8 + Math.PI;
          const y = Math.sin(t) * amplitude * 0.6;
          const cy = h / 2 + y;
          x === 0 ? context.moveTo(x, cy) : context.lineTo(x, cy);
        }
        context.stroke();
      }

      // Faint third wave for very complex states
      if (complexity > 0.75) {
        context.globalAlpha = 0.12;
        context.beginPath();
        for (let x = 0; x < w; x++) {
          const t = x * freq * 1.3 + phaseRef.current * 1.2 + Math.PI * 0.5;
          const y = Math.sin(t) * amplitude * 0.35;
          const cy = h / 2 + y;
          x === 0 ? context.moveTo(x, cy) : context.lineTo(x, cy);
        }
        context.stroke();
      }

      context.globalAlpha = 1;
      const speed =
        0.012 +
        biomeState.motility_activity * 0.03 +
        biomeState.inflammation_score * 0.015;
      phaseRef.current += speed;
      animRef.current = requestAnimationFrame(draw);
    }

    animRef.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(animRef.current);
  }, [biomeState, gutState]);

  return (
    <canvas
      ref={canvasRef}
      className="w-full rounded-lg"
      style={{ height: 120, background: "rgba(255,255,255,0.02)" }}
    />
  );
}
