"use client";

import { useState } from "react";
import { runQuestionnaire, getAudioUrl, type BiomeState, type QuestionnaireResponse } from "@/lib/api";

interface QuestionnairePanelProps {
  genre: string;
  onResult: (
    biomeState: BiomeState,
    audioUrl: string,
    meta: { state: string; mood: string; score: number },
  ) => void;
}

const ACCENT = "0, 229, 160";

export default function QuestionnairePanel({ genre, onResult }: QuestionnairePanelProps) {
  const [fiber, setFiber] = useState(3);
  const [alcohol, setAlcohol] = useState(0);
  const [exercise, setExercise] = useState(30);
  const [stress, setStress] = useState(3);
  const [sleep, setSleep] = useState(7);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await runQuestionnaire({
        fiber_servings: fiber,
        alcohol_units: alcohol,
        exercise_minutes: exercise,
        stress_level: stress,
        sleep_hours: sleep,
        genre,
      });
      onResult(
        res.biome_state,
        getAudioUrl(res.audio_url),
        { state: res.state, mood: res.mood, score: res.score },
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Questionnaire failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-4 w-full">
      <QSlider label="Fiber servings / day" value={fiber} min={0} max={15} step={0.5}
        onChange={setFiber} unit="" hint="fruits, veg, legumes, grains" />
      <QSlider label="Alcohol units" value={alcohol} min={0} max={10} step={0.5}
        onChange={setAlcohol} unit="" hint=">4 units suppresses fermentation" />
      <QSlider label="Exercise (min)" value={exercise} min={0} max={120} step={5}
        onChange={setExercise} unit="min" hint=">30 min boosts H\u2082 production" />
      <QSlider label="Stress level" value={stress} min={1} max={10} step={1}
        onChange={setStress} unit="/10" hint="subjective 1\u201310 scale" />
      <QSlider label="Sleep (hours)" value={sleep} min={0} max={12} step={0.5}
        onChange={setSleep} unit="h" hint="<6h impacts gut pH" />

      <button
        onClick={handleSubmit}
        disabled={loading}
        className="font-mono text-[11px] uppercase tracking-widest py-3 rounded border transition-all"
        style={{
          borderColor: loading ? "rgba(255,255,255,0.07)" : `rgba(${ACCENT}, 0.4)`,
          color: loading ? "rgba(232,237,242,0.2)" : "#00E5A0",
          background: loading ? "transparent" : "rgba(0,229,160,0.06)",
        }}
      >
        {loading ? (
          <span className="animate-pulse">Estimating biomarkers...</span>
        ) : (
          "Generate gut sound"
        )}
      </button>

      {error && (
        <p className="font-mono text-[10px] text-center" style={{ color: "rgb(255,76,76)" }}>{error}</p>
      )}
    </div>
  );
}


function QSlider({
  label, value, min, max, step, onChange, unit, hint,
}: {
  label: string; value: number; min: number; max: number; step: number;
  onChange: (v: number) => void; unit: string; hint: string;
}) {
  return (
    <div>
      <div className="flex justify-between mb-0.5">
        <span className="font-mono text-[9px] uppercase tracking-wider" style={{ color: "rgba(232,237,242,0.5)" }}>
          {label}
        </span>
        <span className="font-mono text-[10px] tabular-nums" style={{ color: `rgb(${ACCENT})` }}>
          {Number.isInteger(value) ? value : value.toFixed(1)}{unit}
        </span>
      </div>
      <input
        type="range"
        min={min} max={max} step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="
          w-full h-1 appearance-none bg-transparent cursor-pointer
          [&::-webkit-slider-thumb]:appearance-none
          [&::-webkit-slider-thumb]:w-2.5 [&::-webkit-slider-thumb]:h-2.5
          [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-accent
          [&::-webkit-slider-runnable-track]:h-[2px]
          [&::-webkit-slider-runnable-track]:bg-surface-light
          [&::-webkit-slider-runnable-track]:rounded-full
        "
      />
      <p className="font-mono text-[8px] mt-0.5" style={{ color: "rgba(232,237,242,0.25)" }}>
        {hint}
      </p>
    </div>
  );
}
