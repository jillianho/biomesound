"use client";

import { useEffect, useRef, useState } from "react";
import WaveSurfer from "wavesurfer.js";

interface AudioPlayerProps {
  audioUrl: string;
}

export default function AudioPlayer({ audioUrl }: AudioPlayerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const wavesurferRef = useRef<WaveSurfer | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [currentTime, setCurrentTime] = useState("0:00");
  const [duration, setDuration] = useState("0:00");

  useEffect(() => {
    if (!containerRef.current) return;

    const ws = WaveSurfer.create({
      container: containerRef.current,
      waveColor: "rgba(0, 240, 255, 0.3)",
      progressColor: "rgba(0, 240, 255, 0.8)",
      cursorColor: "rgba(0, 240, 255, 0.6)",
      cursorWidth: 1,
      barWidth: 2,
      barGap: 1,
      barRadius: 1,
      height: 80,
      normalize: true,
      backend: "WebAudio",
    });

    ws.load(audioUrl);

    ws.on("ready", () => {
      setIsReady(true);
      setDuration(formatTime(ws.getDuration()));
    });

    ws.on("audioprocess", () => {
      setCurrentTime(formatTime(ws.getCurrentTime()));
    });

    ws.on("play", () => setIsPlaying(true));
    ws.on("pause", () => setIsPlaying(false));
    ws.on("finish", () => setIsPlaying(false));

    wavesurferRef.current = ws;

    return () => {
      ws.destroy();
    };
  }, [audioUrl]);

  const togglePlayPause = () => {
    wavesurferRef.current?.playPause();
  };

  return (
    <div className="space-y-4">
      {/* Waveform */}
      <div
        ref={containerRef}
        className="waveform-container rounded-lg bg-surface/30 p-2"
      />

      {/* Controls */}
      <div className="flex items-center justify-between">
        <span className="font-mono text-xs text-muted">
          {currentTime} / {duration}
        </span>

        <button
          onClick={togglePlayPause}
          disabled={!isReady}
          className={`
            w-10 h-10 rounded-full flex items-center justify-center
            transition-all duration-300
            ${
              isReady
                ? "bg-accent/10 hover:bg-accent/20 text-accent border border-accent/30"
                : "bg-surface text-muted border border-surface-light cursor-not-allowed"
            }
          `}
        >
          {isPlaying ? (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <rect x="6" y="4" width="4" height="16" />
              <rect x="14" y="4" width="4" height="16" />
            </svg>
          ) : (
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="currentColor"
              className="ml-0.5"
            >
              <polygon points="5,3 19,12 5,21" />
            </svg>
          )}
        </button>

        <a
          href={audioUrl}
          download="biome_sound.wav"
          className="
            font-mono text-xs text-accent/70 hover:text-accent
            transition-colors duration-200
            border border-accent/20 hover:border-accent/40
            rounded px-3 py-1.5
          "
        >
          Download WAV
        </a>
      </div>
    </div>
  );
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}
