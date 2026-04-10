"use client";

import { useMemo, useEffect, useState, useRef } from "react";
import { FFmpeg } from "@ffmpeg/ffmpeg";
import { fetchFile } from "@ffmpeg/util";

interface GutViewerProps {
  file: File;
}

const BROWSER_PLAYABLE = ["mp4", "webm", "ogg", "mov"];

export default function GutViewer({ file }: GutViewerProps) {
  const objectUrl = useMemo(() => URL.createObjectURL(file), [file]);
  const isVideo = file.type.startsWith("video/") ||
    ["avi", "mkv", "mp4", "mov", "webm", "ogg"].includes(file.name.split(".").pop()?.toLowerCase() || "");
  const ext = file.name.split(".").pop()?.toLowerCase() || "";
  const isBrowserPlayable = isVideo && BROWSER_PLAYABLE.includes(ext);
  const [loaded, setLoaded] = useState(false);
  const [converting, setConverting] = useState(false);
  const [convertedUrl, setConvertedUrl] = useState<string | null>(null);
  const [convertError, setConvertError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const ffmpegRef = useRef<FFmpeg | null>(null);

  // Auto-convert unsupported video formats
  useEffect(() => {
    if (!isVideo || isBrowserPlayable) return;

    let cancelled = false;

    async function convert() {
      setConverting(true);
      setConvertError(null);
      setProgress(0);

      try {
        const ffmpeg = new FFmpeg();
        ffmpegRef.current = ffmpeg;

        ffmpeg.on("progress", ({ progress: p }) => {
          if (!cancelled) setProgress(Math.round(p * 100));
        });

        await ffmpeg.load({
          coreURL: "https://unpkg.com/@ffmpeg/core@0.12.10/dist/umd/ffmpeg-core.js",
          wasmURL: "https://unpkg.com/@ffmpeg/core@0.12.10/dist/umd/ffmpeg-core.wasm",
        });

        if (cancelled) return;

        const inputName = `input.${ext}`;
        const outputName = "output.mp4";

        await ffmpeg.writeFile(inputName, await fetchFile(file));
        await ffmpeg.exec(["-i", inputName, "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28", "-c:a", "aac", "-movflags", "+faststart", outputName]);

        if (cancelled) return;

        const data = await ffmpeg.readFile(outputName);
        // Convert to ArrayBuffer-backed Uint8Array for Blob compatibility
        let blobPart: Uint8Array;
        let arrayBuffer: ArrayBuffer;
        if (data instanceof Uint8Array) {
          // If buffer is not a true ArrayBuffer, copy to a new ArrayBuffer
          if (data.buffer instanceof ArrayBuffer && !(data.buffer instanceof SharedArrayBuffer)) {
            arrayBuffer = data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength);
          } else {
            arrayBuffer = Uint8Array.from(data).buffer;
          }
        } else {
          arrayBuffer = new ArrayBuffer(0);
        }
        const blob = new Blob([arrayBuffer], { type: "video/mp4" });
        setConvertedUrl(URL.createObjectURL(blob));

        // Clean up ffmpeg files
        await ffmpeg.deleteFile(inputName).catch(() => {});
        await ffmpeg.deleteFile(outputName).catch(() => {});
      } catch (err) {
        if (!cancelled) {
          setConvertError("Conversion failed — file uploaded for analysis");
          console.error("FFmpeg conversion error:", err);
        }
      } finally {
        if (!cancelled) {
          setConverting(false);
          setProgress(0);
        }
      }
    }

    convert();

    return () => {
      cancelled = true;
      const term: any = ffmpegRef.current?.terminate?.();
      if (term && typeof term.then === "function") {
        term.catch(() => {});
      }
    };
  }, [file, isVideo, isBrowserPlayable, ext]);

  // Clean up converted URL on unmount
  useEffect(() => {
    return () => {
      if (convertedUrl) URL.revokeObjectURL(convertedUrl);
    };
  }, [convertedUrl]);

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

      {isVideo && (isBrowserPlayable || convertedUrl) ? (
        <video
          src={convertedUrl || objectUrl}
          controls
          onLoadedData={() => setLoaded(true)}
          className="w-full h-auto max-h-[60vh] object-contain"
        />
      ) : isVideo ? (
        <div className="flex flex-col items-center justify-center py-12 px-4 gap-3">
          {converting ? (
            <>
              <div className="w-8 h-8 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
              <span className="font-mono text-[11px] text-accent/60 text-center">
                Converting .{ext} to MP4…
              </span>
              <div className="w-48 h-[3px] rounded-full bg-surface-light overflow-hidden">
                <div
                  className="h-full bg-accent/60 rounded-full transition-all duration-300"
                  style={{ width: `${Math.max(progress, 5)}%` }}
                />
              </div>
              <span className="font-mono text-[9px] text-muted/40">
                {progress}%
              </span>
            </>
          ) : (
            <>
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" className="text-accent/40">
                <rect x="2" y="4" width="20" height="16" rx="2" />
                <path d="M10 9l5 3-5 3V9z" fill="currentColor" opacity="0.3" />
              </svg>
              <span className="font-mono text-[11px] text-muted/60 text-center">
                {file.name}
              </span>
              <span className="font-mono text-[9px] text-muted/40 uppercase tracking-wider">
                {convertError || `.${ext} preview not supported — file uploaded for analysis`}
              </span>
            </>
          )}
        </div>
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
