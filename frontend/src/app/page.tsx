"use client";

import { useState, useEffect, useCallback } from "react";
import ParticleBackground from "@/components/ParticleBackground";
import UploadZone from "@/components/UploadZone";
import ProcessingAnimation from "@/components/ProcessingAnimation";
import BiomeDashboard from "@/components/BiomeDashboard";
import AudioPlayer from "@/components/AudioPlayer";
import GutViewer from "@/components/GutViewer";
import { runPipeline, getAudioUrl, generateFromState, type BiomeState } from "@/lib/api";

type AppState =
  | { view: "landing" }
  | { view: "processing"; file: File; phase: "extracting" | "inferring" | "composing" }
  | { view: "result"; file: File; biomeState: BiomeState; audioUrl: string };

export default function Home() {
  const [state, setState] = useState<AppState>({ view: "landing" });
  const [error, setError] = useState<string | null>(null);
  const [transitioning, setTransitioning] = useState(false);
  const [showSliders, setShowSliders] = useState(false);

  // Smooth view transition helper
  const transitionTo = useCallback((newState: AppState) => {
    setTransitioning(true);
    setTimeout(() => {
      setState(newState);
      setTimeout(() => setTransitioning(false), 50);
    }, 300);
  }, []);

  const handleFileSelected = async (file: File) => {
    setError(null);
    setShowSliders(false);
    transitionTo({ view: "processing", file, phase: "extracting" });

    const phaseTimer1 = setTimeout(() => {
      setState((s) =>
        s.view === "processing" ? { ...s, phase: "inferring" } : s
      );
    }, 2000);
    const phaseTimer2 = setTimeout(() => {
      setState((s) =>
        s.view === "processing" ? { ...s, phase: "composing" } : s
      );
    }, 4000);

    try {
      const result = await runPipeline(file);
      clearTimeout(phaseTimer1);
      clearTimeout(phaseTimer2);

      transitionTo({
        view: "result",
        file,
        biomeState: result.biome_state,
        audioUrl: getAudioUrl(result.audio_url),
      });
    } catch (err) {
      clearTimeout(phaseTimer1);
      clearTimeout(phaseTimer2);
      setError(err instanceof Error ? err.message : "Something went wrong");
      transitionTo({ view: "landing" });
    }
  };

  const handleReset = () => {
    setShowSliders(false);
    transitionTo({ view: "landing" });
    setError(null);
  };

  const handleRegenerate = async () => {
    if (state.view !== "result") return;
    const file = state.file;
    const seed = Math.floor(Math.random() * 100000);
    transitionTo({ view: "processing", file, phase: "composing" });

    try {
      const result = await runPipeline(file, 30, seed);
      transitionTo({
        view: "result",
        file,
        biomeState: result.biome_state,
        audioUrl: getAudioUrl(result.audio_url),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Regeneration failed");
      transitionTo({ view: "landing" });
    }
  };

  const handleBiomeAdjust = async (adjusted: BiomeState) => {
    if (state.view !== "result") return;
    try {
      const audioUrl = await generateFromState(adjusted);
      setState({
        ...state,
        biomeState: adjusted,
        audioUrl,
      });
    } catch {
      // Silently fail on slider adjustments — don't disrupt the view
    }
  };

  const wrapperClass = `transition-opacity duration-300 ${
    transitioning ? "opacity-0" : "opacity-100"
  }`;

  // --- Landing ---
  if (state.view === "landing") {
    return (
      <main className={`relative flex-1 flex flex-col items-center justify-center min-h-screen px-4 ${wrapperClass}`}>
        <ParticleBackground />

        <div className="relative z-10 flex flex-col items-center gap-10 sm:gap-12 w-full max-w-2xl">
          {/* Title */}
          <div className="text-center">
            <h1 className="text-4xl sm:text-5xl md:text-6xl font-light tracking-[0.2em] sm:tracking-[0.3em] text-foreground/90 mb-3 sm:mb-4">
              BIOME SOUND
            </h1>
            <p className="text-muted text-xs sm:text-sm tracking-widest uppercase">
              Your gut composes the music
            </p>
          </div>

          {/* Upload */}
          <UploadZone onFileSelected={handleFileSelected} />

          {/* Error */}
          {error && (
            <div className="animate-[fadeIn_0.3s_ease] text-center">
              <p className="text-accent-red text-sm font-mono max-w-md">
                {error}
              </p>
              <button
                onClick={() => setError(null)}
                className="text-muted hover:text-foreground text-xs font-mono mt-2 transition-colors"
              >
                dismiss
              </button>
            </div>
          )}

          {/* Subtle footer */}
          <p className="absolute bottom-6 text-[10px] text-muted/30 font-mono tracking-wider">
            Art/science project — not a diagnostic tool
          </p>
        </div>
      </main>
    );
  }

  // --- Processing ---
  if (state.view === "processing") {
    return (
      <main className={`relative flex-1 flex items-center justify-center min-h-screen px-4 ${wrapperClass}`}>
        <div className="flex flex-col lg:flex-row items-center gap-10 lg:gap-16 max-w-4xl w-full">
          {/* Image preview */}
          <div className="w-full max-w-[200px] sm:max-w-xs opacity-60">
            <GutViewer file={state.file} />
          </div>

          {/* Animation */}
          <ProcessingAnimation phase={state.phase} />
        </div>
      </main>
    );
  }

  // --- Result ---
  return (
    <main className={`relative flex-1 min-h-screen px-4 py-6 sm:px-8 sm:py-8 lg:px-12 ${wrapperClass}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6 sm:mb-8">
        <button
          onClick={handleReset}
          className="text-muted hover:text-foreground text-xs sm:text-sm font-mono transition-colors duration-200 group flex items-center gap-1.5"
        >
          <span className="inline-block transition-transform group-hover:-translate-x-0.5">&larr;</span>
          New scan
        </button>
        <h1 className="text-[10px] sm:text-sm tracking-[0.2em] text-muted/50 uppercase">
          BIOME SOUND
        </h1>
      </div>

      {/* Dashboard layout */}
      <div className="flex flex-col lg:flex-row gap-6 sm:gap-8 lg:gap-12 max-w-7xl mx-auto">
        {/* Left: Image */}
        <div className="lg:w-[40%] lg:sticky lg:top-8 lg:self-start">
          <GutViewer file={state.file} />
        </div>

        {/* Right: Data + Audio */}
        <div className="lg:w-[60%] flex flex-col gap-6 sm:gap-8">
          {/* Biome parameters */}
          <section>
            <h2 className="text-[10px] sm:text-xs uppercase tracking-widest text-muted/60 mb-3 sm:mb-4">
              Inferred Biome State
            </h2>
            <BiomeDashboard
              biomeState={state.biomeState}
              onAdjust={showSliders ? handleBiomeAdjust : undefined}
            />
          </section>

          {/* Audio */}
          <section>
            <h2 className="text-[10px] sm:text-xs uppercase tracking-widest text-muted/60 mb-3 sm:mb-4">
              Sonification
            </h2>
            <AudioPlayer audioUrl={state.audioUrl} />
          </section>

          {/* Actions */}
          <div className="flex flex-wrap gap-3">
            <button
              onClick={handleRegenerate}
              className="
                font-mono text-[11px] sm:text-xs
                text-muted hover:text-accent
                border border-surface-light hover:border-accent/30
                rounded px-3 sm:px-4 py-2
                transition-all duration-300
              "
            >
              Regenerate
            </button>
            <button
              onClick={() => setShowSliders(!showSliders)}
              className={`
                font-mono text-[11px] sm:text-xs
                border rounded px-3 sm:px-4 py-2
                transition-all duration-300
                ${
                  showSliders
                    ? "text-accent border-accent/30 bg-accent/5"
                    : "text-muted hover:text-accent border-surface-light hover:border-accent/30"
                }
              `}
            >
              {showSliders ? "Lock parameters" : "Adjust parameters"}
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}
