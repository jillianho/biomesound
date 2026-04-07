"use client";

import { useMemo, useEffect, useState } from "react";

interface GutViewerProps {
  file: File;
}

export default function GutViewer({ file }: GutViewerProps) {
  const objectUrl = useMemo(() => URL.createObjectURL(file), [file]);
  const isVideo = file.type.startsWith("video/");
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    setLoaded(false);
    const timer = setTimeout(() => setLoaded(true), 100);
    return () => clearTimeout(timer);
  }, [file]);

  return (
    <div
      className="relative rounded-lg overflow-hidden bg-surface/30"
      style={{
        opacity: loaded ? 1 : 0,
        transform: loaded ? "scale(1)" : "scale(0.98)",
        transition: "opacity 0.8s ease, transform 0.8s ease",
      }}
    >
      {/* Animated scan-line sweep */}
      <div
        className="absolute inset-0 z-20 pointer-events-none"
        style={{
          background:
            "linear-gradient(180deg, transparent 0%, rgba(0,240,255,0.03) 50%, transparent 100%)",
          backgroundSize: "100% 200%",
          animation: "scanSweep 8s linear infinite",
        }}
      />

      {/* Static scan-lines */}
      <div
        className="absolute inset-0 z-10 pointer-events-none opacity-[0.04]"
        style={{
          backgroundImage:
            "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,240,255,0.15) 2px, rgba(0,240,255,0.15) 3px)",
        }}
      />

      {/* Vignette */}
      <div
        className="absolute inset-0 z-10 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse at center, transparent 40%, rgba(10,10,15,0.7) 100%)",
        }}
      />

      {/* Corner markers — medical imaging aesthetic */}
      {[
        "top-2 left-2",
        "top-2 right-2 rotate-90",
        "bottom-2 left-2 -rotate-90",
        "bottom-2 right-2 rotate-180",
      ].map((pos, i) => (
        <div
          key={i}
          className={`absolute z-20 pointer-events-none ${pos}`}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M0 8V0H8" stroke="rgba(0,240,255,0.3)" strokeWidth="1" />
          </svg>
        </div>
      ))}

      {/* Subtle teal tint overlay */}
      <div
        className="absolute inset-0 z-10 pointer-events-none mix-blend-overlay"
        style={{ backgroundColor: "rgba(0, 240, 255, 0.03)" }}
      />

      {isVideo ? (
        <video
          src={objectUrl}
          controls
          onLoadedData={() => setLoaded(true)}
          className="w-full h-auto max-h-[60vh] object-contain"
        />
      ) : (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={objectUrl}
          alt="Gut endoscopy image"
          onLoad={() => setLoaded(true)}
          className="w-full h-auto max-h-[60vh] object-contain"
        />
      )}

      {/* Filename label */}
      <div className="absolute bottom-2 right-2 z-20 pointer-events-none">
        <span className="font-mono text-[9px] text-accent/30 tracking-wider">
          {file.name}
        </span>
      </div>

      <style jsx>{`
        @keyframes scanSweep {
          0% { background-position: 0% 0%; }
          100% { background-position: 0% 200%; }
        }
      `}</style>
    </div>
  );
}
