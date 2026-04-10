"use client";
import { useEffect, useRef } from "react";

interface WaveformAnimationProps {
  color?: string;
  complexity?: number; // 0-1
  inflammation?: number; // 0-1
  height?: number;
}

// Simple animated waveform, inspired by gut_radio_dashboard.html
export default function WaveformAnimation({ color = "#00E5A0", complexity = 0.5, inflammation = 0, height = 60 }: WaveformAnimationProps) {

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const phaseRef = useRef(0);
  const animRef = useRef<number>();

  useEffect(() => {
    let running = true;
    const draw = () => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      // Responsive sizing
      const dpr = window.devicePixelRatio || 1;
      const width = canvas.offsetWidth * dpr;
      const h = (height || 120) * dpr;
      canvas.width = width;
      canvas.height = h;
      ctx.clearRect(0, 0, width, h);

      // Main waveform
      const amp = h * 0.28 * (0.3 + (complexity ?? 0.5) * 0.7);
      const freq = 0.012 + (complexity ?? 0.5) * 0.018;
      const chaos = (inflammation ?? 0) * 0.6;
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5 * dpr;
      ctx.globalAlpha = 0.85;
      ctx.beginPath();
      for (let x = 0; x < width; x++) {
        const t = x * freq + phaseRef.current;
        let y = Math.sin(t) * amp;
        if ((complexity ?? 0.5) > 0.4) y += Math.sin(t * 2.1 + 0.5) * amp * 0.4 * (complexity ?? 0.5);
        if ((complexity ?? 0.5) > 0.65) y += Math.sin(t * 3.7 + 1.2) * amp * 0.25 * (complexity ?? 0.5);
        if (chaos > 0.2) y += (Math.random() - 0.5) * amp * chaos * 0.5;
        const cy = h / 2 + y;
        x === 0 ? ctx.moveTo(x, cy) : ctx.lineTo(x, cy);
      }
      ctx.stroke();

      // Subtle second wave for healthy/complex states
      if ((complexity ?? 0.5) > 0.55) {
        ctx.globalAlpha = 0.25;
        ctx.strokeStyle = color;
        ctx.beginPath();
        for (let x = 0; x < width; x++) {
          const t = x * freq * 0.7 + phaseRef.current * 0.8 + Math.PI;
          const y = Math.sin(t) * amp * 0.6;
          const cy = h / 2 + y;
          x === 0 ? ctx.moveTo(x, cy) : ctx.lineTo(x, cy);
        }
        ctx.stroke();
      }

      ctx.globalAlpha = 1;
      // Animate phase (motility and inflammation affect speed)
      const speed = 0.012 + (complexity ?? 0.5) * 0.03 + (inflammation ?? 0) * 0.015;
      phaseRef.current += speed;
      if (running) animRef.current = requestAnimationFrame(draw);
    };
    draw();
    return () => {
      running = false;
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, [color, complexity, inflammation, height]);

  return (
    <canvas
      ref={canvasRef}
      width={320}
      height={height}
      style={{ width: "100%", height: height, display: "block", background: "rgba(0,229,160,0.04)", borderRadius: 8 }}
    />
  );
}
