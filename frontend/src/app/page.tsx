"use client";

import { useState, useCallback } from "react";
import ParticleBackground from "@/components/ParticleBackground";
import UploadZone from "@/components/UploadZone";
import ProcessingAnimation from "@/components/ProcessingAnimation";
import BiomeDashboard from "@/components/BiomeDashboard";
import AudioPlayer from "@/components/AudioPlayer";
import GutViewer from "@/components/GutViewer";
import HowItWorks from "@/components/HowItWorks";
import SensorPanel from "@/components/SensorPanel";
import GutInsights from "@/components/GutInsights";
import { runPipeline, getAudioUrl, generateFromState, type BiomeState } from "@/lib/api";
import BacteriaGuide from "@/components/BacteriaGuide";

type InputMode = "image" | "sensor";
type ResultTab = "biome" | "insights" | "bacteria";

interface ResultMeta {
  state: string;
  mood: string;
  score: number;
}

type AppState =
  | { view: "landing" }
  | { view: "processing"; file: File; phase: "extracting" | "inferring" | "composing" }
  | { view: "result"; file?: File; biomeState: BiomeState; audioUrl: string; meta?: ResultMeta };

// mood descriptions matching sensor_inference.py states
const MOOD_DESCRIPTIONS: Record<string, string> = {
  peak_diversity: "Maximum fiber fermentation — multiple bacterial phyla active simultaneously. Full orchestra: layered strings, percussion, piano, melodic lead.",
  healthy:        "Balanced pH, active H₂ fermentation. Bacteroides and Bifidobacterium thriving. Warm, layered jazz with melodic lead.",
  fasted:         "Low fermentation substrate. Microbiome quiet, not distressed. Single acoustic instrument, slow tempo, ambient pads.",
  methanogen:     "Methanobrevibacter smithii consuming hydrogen. Slow motility detected. Heavy bass drone, deep sustained tones.",
  dysbiosis:      "Beneficial bacteria crashing. pH disruption detected. Instruments dropping out — dissonant intervals emerging.",
  inflamed:       "Active mucosal inflammation. Proteobacteria blooming. Distorted FM synthesis, irregular rhythm, high-frequency noise.",
};

const STATE_COLORS: Record<string, string> = {
  peak_diversity: "0, 240, 200",
  healthy:        "0, 240, 200",
  fasted:         "91, 155, 213",
  methanogen:     "245, 166, 35",
  dysbiosis:      "255, 140, 66",
  inflamed:       "255, 69, 88",
};

function deriveScore(b: BiomeState): number {
  return Math.round(
    (b.diversity_index * 35 + b.mucosal_integrity * 25 + (1 - b.inflammation_score) * 25 + b.metabolic_energy * 15)
  );
}

function deriveMood(b: BiomeState): { state: string; mood: string } {
  const d = b.diversity_index;
  const inf = b.inflammation_score;
  const mot = b.motility_activity;
  const prot = b.proteobacteria_bloom;

  if (inf > 0.65) return { state: "inflamed", mood: "System alert" };
  if (prot > 0.55 && d < 0.4) return { state: "dysbiosis", mood: "Dissonance" };
  if ((1 - mot) > 0.65 && d < 0.5) return { state: "methanogen", mood: "Heavy drone" };
  if (d > 0.75 && inf < 0.2) return { state: "peak_diversity", mood: "Full ensemble" };
  if (d > 0.45 && inf < 0.35) return { state: "healthy", mood: "Smooth fermentation" };
  return { state: "fasted", mood: "Resting baseline" };
}

export default function Home() {
  const [state, setState] = useState<AppState>({ view: "landing" });
  const [inputMode, setInputMode] = useState<InputMode>("image");
  const [resultTab, setResultTab] = useState<ResultTab>("biome");
  const [error, setError] = useState<string | null>(null);
  const [transitioning, setTransitioning] = useState(false);
  const [showSliders, setShowSliders] = useState(false);

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
    setResultTab("biome");
    transitionTo({ view: "processing", file, phase: "extracting" });
    const t1 = setTimeout(() => setState((s) => s.view === "processing" ? { ...s, phase: "inferring" } : s), 2000);
    const t2 = setTimeout(() => setState((s) => s.view === "processing" ? { ...s, phase: "composing" } : s), 4000);
    try {
      const result = await runPipeline(file);
      clearTimeout(t1); clearTimeout(t2);
      const { state: gutState, mood } = deriveMood(result.biome_state);
      transitionTo({
        view: "result", file,
        biomeState: result.biome_state,
        audioUrl: getAudioUrl(result.audio_url),
        meta: { state: gutState, mood, score: deriveScore(result.biome_state) },
      });
    } catch (err) {
      clearTimeout(t1); clearTimeout(t2);
      setError(err instanceof Error ? err.message : "Something went wrong");
      transitionTo({ view: "landing" });
    }
  };

  const handleSensorResult = useCallback((biomeState: BiomeState, audioUrl: string, meta: ResultMeta) => {
    setResultTab("biome");
    setState({ view: "result", biomeState, audioUrl, meta });
  }, []);

  const handleReset = () => { setShowSliders(false); transitionTo({ view: "landing" }); setError(null); };

  const handleRegenerate = async () => {
    if (state.view !== "result" || !state.file) return;
    const seed = Math.floor(Math.random() * 100000);
    transitionTo({ view: "processing", file: state.file, phase: "composing" });
    try {
      const result = await runPipeline(state.file, 30, seed);
      const { state: gutState, mood } = deriveMood(result.biome_state);
      transitionTo({ view: "result", file: state.file, biomeState: result.biome_state, audioUrl: getAudioUrl(result.audio_url), meta: { state: gutState, mood, score: deriveScore(result.biome_state) } });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Regeneration failed");
      transitionTo({ view: "landing" });
    }
  };

  const handleBiomeAdjust = async (adjusted: BiomeState) => {
    if (state.view !== "result") return;
    try {
      const audioUrl = await generateFromState(adjusted);
      const { state: gutState, mood } = deriveMood(adjusted);
      setState({ ...state, biomeState: adjusted, audioUrl, meta: { state: gutState, mood, score: deriveScore(adjusted) } });
    } catch { /* silent */ }
  };

  const wrapClass = `transition-opacity duration-300 ${transitioning ? "opacity-0" : "opacity-100"}`;

  // ── Landing ──────────────────────────────────────────────────────────
  if (state.view === "landing") {
    return (
      <main className={`relative flex-1 flex flex-col items-center justify-center min-h-screen px-4 ${wrapClass}`}>
        <ParticleBackground />
        <div className="relative z-10 flex flex-col items-center gap-10 w-full max-w-2xl">
          <div className="text-center">
            <h1 className="text-4xl sm:text-5xl md:text-6xl font-light tracking-[0.2em] sm:tracking-[0.3em] text-foreground/90 mb-3">
              BIOME SOUND
            </h1>
            <p className="text-muted text-xs sm:text-sm tracking-widest uppercase">
              Your gut composes the music
            </p>
          </div>

          <div className="flex gap-0 border border-surface-light rounded overflow-hidden">
            <button onClick={() => setInputMode("image")} className={`font-mono text-[11px] uppercase tracking-widest px-5 py-2 transition-all duration-200 border-r border-surface-light ${inputMode === "image" ? "bg-accent/10 text-accent" : "text-muted hover:text-foreground"}`}>
              Image / Video
            </button>
            <button onClick={() => setInputMode("sensor")} className={`font-mono text-[11px] uppercase tracking-widest px-5 py-2 transition-all duration-200 ${inputMode === "sensor" ? "bg-accent/10 text-accent" : "text-muted hover:text-foreground"}`}>
              Sensor input
            </button>
          </div>

          {inputMode === "image" ? (
            <UploadZone onFileSelected={handleFileSelected} />
          ) : (
            <div className="w-full border border-surface-light rounded p-6">
              <p className="font-mono text-[10px] uppercase tracking-widest text-muted/40 mb-4">Pillbot sensor readings</p>
              <SensorPanel onResult={handleSensorResult} />
            </div>
          )}

          {error && (
            <div className="text-center">
              <p className="text-accent-red text-sm font-mono max-w-md">{error}</p>
              <button onClick={() => setError(null)} className="text-muted hover:text-foreground text-xs font-mono mt-2 transition-colors">dismiss</button>
            </div>
          )}
          <HowItWorks />
          <p className="absolute bottom-6 text-[10px] text-muted/30 font-mono tracking-wider">Art/science project — not a diagnostic tool</p>
        </div>
      </main>
    );
  }

  // ── Processing ───────────────────────────────────────────────────────
  if (state.view === "processing") {
    return (
      <main className={`relative flex-1 flex items-center justify-center min-h-screen px-4 ${wrapClass}`}>
        <div className="flex flex-col lg:flex-row items-center gap-10 lg:gap-16 max-w-4xl w-full">
          {state.file && <div className="w-full max-w-xs opacity-60"><GutViewer file={state.file} /></div>}
          <ProcessingAnimation phase={state.phase} />
        </div>
      </main>
    );
  }

  // ── Result ───────────────────────────────────────────────────────────
  const meta = state.view === "result" ? state.meta : undefined;
  const gutState = meta?.state || "healthy";
  const rgb = STATE_COLORS[gutState] || "0,240,200";
  const score = meta?.score ?? deriveScore(state.biomeState);
  const mood = meta?.mood || "Smooth fermentation";
  const moodDesc = MOOD_DESCRIPTIONS[gutState] || MOOD_DESCRIPTIONS["healthy"];

  return (
    <main className={`relative flex-1 min-h-screen px-4 py-6 sm:px-8 lg:px-12 ${wrapClass}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6 sm:mb-8">
        <button onClick={handleReset} className="text-muted hover:text-foreground text-xs sm:text-sm font-mono transition-colors group flex items-center gap-1.5">
          <span className="inline-block transition-transform group-hover:-translate-x-0.5">&larr;</span>
          New scan
        </button>
        <h1 className="text-[10px] sm:text-sm tracking-[0.2em] text-muted/50 uppercase">BIOME SOUND</h1>
      </div>

      <div className="flex flex-col lg:flex-row gap-6 sm:gap-8 lg:gap-12 max-w-7xl mx-auto">

        {/* ── LEFT COLUMN ── */}
        <div className="lg:w-[38%] flex flex-col gap-5 lg:sticky lg:top-8 lg:self-start">

          {/* BIG GUT SCORE CARD */}
          <div
            className="rounded border p-5"
            style={{ borderColor: `rgba(${rgb}, 0.25)`, background: `rgba(${rgb}, 0.04)` }}
          >
            <p className="font-mono text-[9px] uppercase tracking-[0.18em] mb-2" style={{ color: `rgba(${rgb}, 0.6)` }}>
              Gut score
            </p>
            <div className="flex items-end justify-between gap-4 mb-3">
              {/* Big number */}
              <span
                className="font-mono leading-none"
                style={{ fontSize: "72px", fontWeight: 700, color: `rgb(${rgb})`, letterSpacing: "-0.02em", lineHeight: 1 }}
              >
                {score}
              </span>
              {/* Mood + state */}
              <div className="text-right pb-1">
                <p className="font-mono text-[9px] uppercase tracking-[0.15em] mb-1" style={{ color: `rgba(${rgb}, 0.5)` }}>
                  Music mood
                </p>
                <p className="text-base font-light" style={{ color: `rgb(${rgb})` }}>{mood}</p>
                <p className="font-mono text-[9px] uppercase tracking-wider mt-1" style={{ color: "rgba(200,212,224,0.35)" }}>
                  {gutState.replace(/_/g, " ")}
                </p>
              </div>
            </div>

            {/* Score bar */}
            <div className="h-[2px] rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.06)" }}>
              <div
                className="h-full rounded-full transition-all duration-1000"
                style={{ width: `${score}%`, background: `rgb(${rgb})`, boxShadow: `0 0 8px rgba(${rgb},0.4)` }}
              />
            </div>

            {/* Mood description */}
            <p className="mt-3 text-[11px] leading-relaxed" style={{ color: "rgba(200,212,224,0.5)" }}>
              {moodDesc}
            </p>
          </div>

          {/* Image viewer OR sensor panel */}
          {state.file ? (
            <GutViewer file={state.file} />
          ) : (
            <div className="border border-surface-light rounded p-5">
              <p className="font-mono text-[10px] uppercase tracking-widest text-muted/40 mb-4">Adjust sensor readings</p>
              <SensorPanel onResult={handleSensorResult} />
            </div>
          )}

          {/* Audio player */}
          <section>
            <h2 className="font-mono text-[10px] uppercase tracking-widest text-muted/40 mb-3">Sonification</h2>
            <AudioPlayer audioUrl={state.audioUrl} />
          </section>

          {/* Actions */}
          <div className="flex flex-wrap gap-3">
            {state.file && (
              <button onClick={handleRegenerate} className="font-mono text-[11px] text-muted hover:text-accent border border-surface-light hover:border-accent/30 rounded px-4 py-2 transition-all duration-300">
                Regenerate
              </button>
            )}
            <button
              onClick={() => setShowSliders(!showSliders)}
              className={`font-mono text-[11px] border rounded px-4 py-2 transition-all duration-300 ${showSliders ? "text-accent border-accent/30 bg-accent/5" : "text-muted hover:text-accent border-surface-light hover:border-accent/30"}`}
            >
              {showSliders ? "Lock parameters" : "Adjust parameters"}
            </button>
          </div>
        </div>

        {/* ── RIGHT COLUMN ── */}
        <div className="lg:w-[62%] flex flex-col gap-6">

          {/* Tab switcher */}
          <div className="flex gap-6 border-b border-surface-light pb-0">
            {(["biome", "insights", "bacteria"] as ResultTab[]).map((tab) => (
              <button
                key={tab}
                onClick={() => setResultTab(tab)}
                className={`font-mono text-[10px] uppercase tracking-widest pb-3 border-b-2 transition-all duration-200 ${
                  resultTab === tab
                    ? "text-accent border-accent"
                    : "text-muted border-transparent hover:text-foreground"
                }`}
                style={{ marginBottom: "-1px" }}
              >
                {tab === "biome" ? "Biome state" : tab === "insights" ? "How to improve" : "Bacteria guide"}
              </button>
            ))}
          </div>

          {/* Biome dashboard tab */}
          {resultTab === "biome" && (
            <section>
              <BiomeDashboard
                biomeState={state.biomeState}
                onAdjust={showSliders ? handleBiomeAdjust : undefined}
              />
            </section>
          )}

          {/* Insights tab */}
          {resultTab === "insights" && (
            <GutInsights
              biomeState={state.biomeState}
              gutScore={score}
              mood={mood}
              gutStateLabel={gutState}
            />
          )}

          {/* Bacteria guide tab */}
          {resultTab === "bacteria" && (
            <BacteriaGuide
              biomeState={state.biomeState}
              gutScore={score}
              mood={mood}
              gutStateLabel={gutState}
            />
          )}
        </div>
      </div>
    </main>
  );
}
