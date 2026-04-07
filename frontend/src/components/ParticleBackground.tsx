"use client";

import { useEffect, useRef } from "react";

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  baseOpacity: number;
  phase: number; // for organic pulsing
  phaseSpeed: number;
  depth: number; // 0-1, parallax layer
}

export default function ParticleBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationId: number;
    let time = 0;
    const particles: Particle[] = [];
    const PARTICLE_COUNT = 80;

    function resize() {
      canvas!.width = window.innerWidth;
      canvas!.height = window.innerHeight;
    }
    resize();
    window.addEventListener("resize", resize);

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const depth = Math.random();
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.2 * (0.3 + depth * 0.7),
        vy: (Math.random() - 0.5) * 0.2 * (0.3 + depth * 0.7),
        radius: (Math.random() * 1.2 + 0.3) * (0.5 + depth * 0.8),
        baseOpacity: (Math.random() * 0.12 + 0.02) * (0.4 + depth * 0.6),
        phase: Math.random() * Math.PI * 2,
        phaseSpeed: 0.005 + Math.random() * 0.015,
        depth,
      });
    }

    function draw() {
      time += 0.016;
      ctx!.clearRect(0, 0, canvas!.width, canvas!.height);

      // Global slow flow field
      const flowX = Math.sin(time * 0.1) * 0.15;
      const flowY = Math.cos(time * 0.07) * 0.1;

      for (const p of particles) {
        // Organic motion: flow field + own velocity + sinusoidal drift
        p.x += p.vx + flowX * p.depth + Math.sin(time * 0.3 + p.phase) * 0.05;
        p.y += p.vy + flowY * p.depth + Math.cos(time * 0.25 + p.phase) * 0.04;

        // Wrap
        if (p.x < -10) p.x = canvas!.width + 10;
        if (p.x > canvas!.width + 10) p.x = -10;
        if (p.y < -10) p.y = canvas!.height + 10;
        if (p.y > canvas!.height + 10) p.y = -10;

        // Pulsing opacity
        p.phase += p.phaseSpeed;
        const pulse = 0.6 + 0.4 * Math.sin(p.phase);
        const opacity = p.baseOpacity * pulse;

        // Glow effect for larger particles
        if (p.radius > 1.0) {
          const gradient = ctx!.createRadialGradient(
            p.x, p.y, 0, p.x, p.y, p.radius * 4
          );
          gradient.addColorStop(0, `rgba(0, 240, 255, ${opacity * 0.6})`);
          gradient.addColorStop(1, "rgba(0, 240, 255, 0)");
          ctx!.beginPath();
          ctx!.arc(p.x, p.y, p.radius * 4, 0, Math.PI * 2);
          ctx!.fillStyle = gradient;
          ctx!.fill();
        }

        // Core dot
        ctx!.beginPath();
        ctx!.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx!.fillStyle = `rgba(0, 240, 255, ${opacity})`;
        ctx!.fill();
      }

      // Connections — only between particles of similar depth
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          if (Math.abs(particles[i].depth - particles[j].depth) > 0.3) continue;

          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = dx * dx + dy * dy; // skip sqrt for perf
          const maxDist = 14400; // 120^2

          if (dist < maxDist) {
            const alpha = 0.035 * (1 - dist / maxDist) *
              Math.min(particles[i].depth, particles[j].depth);
            ctx!.beginPath();
            ctx!.moveTo(particles[i].x, particles[i].y);
            ctx!.lineTo(particles[j].x, particles[j].y);
            ctx!.strokeStyle = `rgba(0, 240, 255, ${alpha})`;
            ctx!.lineWidth = 0.5;
            ctx!.stroke();
          }
        }
      }

      animationId = requestAnimationFrame(draw);
    }

    draw();

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none"
      style={{ zIndex: 0 }}
    />
  );
}
