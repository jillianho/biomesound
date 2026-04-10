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
import WaveformAnimation from "@/components/WaveformAnimation";

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

function scoreLabel(s: number): string {
  if (s >= 85) return "Peak diversity — gut thriving";
  if (s >= 70) return "Good diversity — healthy fermentation";
  if (s >= 50) return "Moderate activity — room to improve";
  if (s >= 30) return "Low activity — disrupted state";
  return "Critical — inflammation or dysbiosis";
}

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
            <p className="font-mono text-[15px] tracking-[0.12em] uppercase mb-2" style={{ color: "#00E5A0" }}>
              Biome <span style={{ color: "rgba(0,229,160,0.45)" }}>///</span> Sound
            </p>
            <p className="font-mono text-[11px] tracking-[0.15em] uppercase" style={{ color: "rgba(232,237,242,0.45)" }}>
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

  const CELL = "p-7 flex flex-col" as const;
  const LABEL = "font-mono text-[10px] uppercase tracking-[0.15em] mb-4 flex-shrink-0" as const;

  return (
    <main className={`flex-1 flex flex-col ${wrapClass}`} style={{ background: "#080C0F" }}>

      {/* ── Header ── */}
      <header
        className="flex items-center justify-between px-8 py-5 flex-shrink-0"
        style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}
      >
        <span className="font-mono text-[13px] tracking-[0.12em] uppercase" style={{ color: "#00E5A0" }}>
          Biome <span style={{ color: "rgba(0,229,160,0.45)" }}>///</span> Sound
        </span>
        <div className="flex items-center gap-2.5">
          <span className="w-2 h-2 rounded-full animate-pulse" style={{ background: `rgb(${rgb})` }} />
          <span className="font-mono text-[11px]" style={{ color: "rgba(232,237,242,0.45)" }}>
            {gutState.replace(/_/g, " ")}
          </span>
        </div>
      </header>

      {/* ── Dashboard grid ── */}
      <div
        className="result-grid flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-2 gap-px"
        style={{ background: "rgba(255,255,255,0.07)" }}
      >

        {/* ── Score cell ── */}
        <div className={`${CELL} justify-between`} style={{ background: "#080C0F" }}>
          <p className={LABEL} style={{ color: "rgba(232,237,242,0.45)" }}>Gut score</p>
          <div>
            <span
              className="font-mono font-bold leading-none block"
              style={{ fontSize: 80, color: `rgb(${rgb})`, letterSpacing: "-0.03em" }}
            >
              {score}
            </span>
            <p className="text-[13px] mt-2" style={{ color: "rgba(232,237,242,0.45)" }}>
              {scoreLabel(score)}
            </p>
          </div>
          <div className="h-[3px] rounded-sm overflow-hidden mt-4" style={{ background: "rgba(255,255,255,0.07)" }}>
            <div
              className="h-full rounded-sm transition-all duration-1000"
              style={{ width: `${score}%`, background: `rgb(${rgb})` }}
            />
          </div>
        </div>

        {/* ── Mood cell ── */}
        <div className={`${CELL} justify-between`} style={{ background: "#080C0F" }}>
          <p className={LABEL} style={{ color: "rgba(232,237,242,0.45)" }}>Music mood</p>
          <div>
            <p className="text-[36px] font-medium leading-tight" style={{ color: `rgb(${rgb})` }}>{mood}</p>
            <span
              className="inline-block font-mono text-[10px] px-3 py-1 rounded-full border mt-3 uppercase tracking-widest"
              style={{ borderColor: `rgb(${rgb})`, color: `rgb(${rgb})` }}
            >
              {gutState.replace(/_/g, " ")}
            </span>
          </div>
          <p className="text-[12px] leading-relaxed mt-4" style={{ color: "rgba(232,237,242,0.45)" }}>
            {moodDesc}
          </p>
        </div>

        {/* ── Left panel: viewer + audio + actions ── */}
        <div className={`${CELL} gap-5 overflow-y-auto`} style={{ background: "#080C0F" }}>
          <div>
            <p className={LABEL} style={{ color: "rgba(232,237,242,0.45)" }}>
              {state.file ? "Input" : "Sensor readings"}
            </p>
            {state.file ? (
              <GutViewer file={state.file} />
            ) : (
              <SensorPanel onResult={handleSensorResult} />
            )}
          </div>

          <div>
            <p className={LABEL} style={{ color: "rgba(232,237,242,0.45)" }}>Sonification</p>
            <AudioPlayer audioUrl={state.audioUrl} />
          </div>

          <div className="flex flex-wrap gap-2 mt-auto pt-1">
            {state.file && (
              <button
                onClick={handleRegenerate}
                className="font-mono text-[11px] px-4 py-2 rounded border border-white/[0.07] text-muted hover:border-accent/30 hover:text-accent transition-all"
              >
                Regenerate
              </button>
            )}
            <button
              onClick={() => setShowSliders(!showSliders)}
              className="font-mono text-[11px] px-4 py-2 rounded border transition-all"
              style={{
                borderColor: showSliders ? "rgba(0,229,160,0.3)" : "rgba(255,255,255,0.07)",
                color: showSliders ? "#00E5A0" : "rgba(232,237,242,0.45)",
                background: showSliders ? "rgba(0,229,160,0.04)" : "transparent",
              }}
            >
              {showSliders ? "Lock parameters" : "Adjust parameters"}
            </button>
            <button
              onClick={handleReset}
              className="font-mono text-[11px] px-4 py-2 rounded border border-white/[0.07] text-muted hover:text-foreground transition-all"
            >
              ← New scan
            </button>
          </div>
        </div>

        {/* ── Right panel: tabs + content ── */}
        <div className="flex flex-col overflow-hidden" style={{ background: "#080C0F" }}>
          {/* Tab bar */}
          <div className="flex flex-shrink-0" style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
            {([
              { id: "biome"    as ResultTab, label: "Biome state" },
              { id: "insights" as ResultTab, label: "How to improve" },
              { id: "bacteria" as ResultTab, label: "Bacteria guide" },
            ]).map(({ id, label }) => (
              <button
                key={id}
                onClick={() => setResultTab(id)}
                className="flex-1 font-mono text-[10px] uppercase tracking-[0.1em] py-3.5 border-r last:border-r-0 transition-colors"
                style={{
                  borderColor: "rgba(255,255,255,0.07)",
                  color: resultTab === id ? "#00E5A0" : "rgba(232,237,242,0.35)",
                  background: resultTab === id ? "rgba(0,229,160,0.04)" : "transparent",
                }}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="flex-1 overflow-y-auto p-7">
            {resultTab === "biome" && (
              <BiomeDashboard
                biomeState={state.biomeState}
                onAdjust={showSliders ? handleBiomeAdjust : undefined}
              />
            )}
            {resultTab === "insights" && (
              <GutInsights
                biomeState={state.biomeState}
                gutScore={score}
                mood={mood}
                gutStateLabel={gutState}
              />
            )}
            {resultTab === "bacteria" && (
              <BacteriaGuide biomeState={state.biomeState} />
            )}
          </div>
        </div>

        {/* ── Waveform strip — full width ── */}
        <div
          className="lg:col-span-2 flex flex-col flex-shrink-0"
          style={{ background: "#080C0F", height: "180px" }}
        >
          <p
            className="font-mono text-[10px] uppercase tracking-[0.15em] px-8 pt-4 mb-1 flex-shrink-0"
            style={{ color: "rgba(232,237,242,0.45)" }}
          >
            Waveform
          </p>
          <div className="flex-1 min-h-0 px-8 pb-4">
            <WaveformAnimation
              color={`rgb(${rgb})`}
              complexity={state.biomeState.diversity_index}
              inflammation={state.biomeState.inflammation_score}
              height={120}
            />
          </div>
        </div>

      </div>
    </main>
  );
}
