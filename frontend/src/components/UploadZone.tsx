"use client";

import { useCallback, useState, useRef } from "react";

interface UploadZoneProps {
  onFileSelected: (file: File) => void;
}

const ACCEPTED_TYPES = [
  "image/jpeg",
  "image/png",
  "image/tiff",
  "video/mp4",
  "video/quicktime",
];

const ACCEPTED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".tiff", ".tif", ".mp4", ".mov"];

export default function UploadZone({ onFileSelected }: UploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    (file: File) => {
      const ext = "." + file.name.split(".").pop()?.toLowerCase();
      if (ACCEPTED_TYPES.includes(file.type) || ACCEPTED_EXTENSIONS.includes(ext)) {
        onFileSelected(file);
      }
    },
    [onFileSelected]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  return (
    <div
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onClick={() => inputRef.current?.click()}
      className={`
        relative cursor-pointer
        w-full max-w-lg mx-auto
        py-16 px-8
        rounded-lg
        transition-all duration-500 ease-out
        ${
          isDragging
            ? "bg-accent/5 shadow-[0_0_40px_rgba(0,240,255,0.1)]"
            : "bg-transparent hover:bg-surface/50"
        }
      `}
    >
      {/* Border effect */}
      <div
        className={`
          absolute inset-0 rounded-lg
          transition-all duration-500
          ${
            isDragging
              ? "border border-accent/40"
              : "border border-surface-light/50 hover:border-muted/30"
          }
        `}
      />

      <div className="relative z-10 text-center">
        {/* Upload icon */}
        <div className="mb-6 flex justify-center">
          <svg
            width="48"
            height="48"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1"
            className={`transition-colors duration-300 ${
              isDragging ? "text-accent" : "text-muted"
            }`}
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
        </div>

        <p className="text-foreground/80 text-sm mb-2">
          Drop endoscopy image or video
        </p>
        <p className="text-muted text-xs font-mono">
          JPG, PNG, TIFF, MP4, MOV
        </p>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_EXTENSIONS.join(",")}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFile(file);
        }}
        className="hidden"
      />
    </div>
  );
}
