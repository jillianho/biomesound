const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface BiomeState {
  diversity_index: number;
  inflammation_score: number;
  firmicutes_dominance: number;
  bacteroidetes_dominance: number;
  proteobacteria_bloom: number;
  motility_activity: number;
  mucosal_integrity: number;
  metabolic_energy: number;
}

export interface PipelineResponse {
  biome_state: BiomeState;
  audio_url: string;
  features: Record<string, number>[];
  frames_analyzed: number;
}

export async function runPipeline(
  file: File,
  durationSeconds: number = 30,
  seed?: number,
  genre: string = "classical",
): Promise<PipelineResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const params = new URLSearchParams();
  params.set("duration_seconds", String(durationSeconds));
  params.set("genre", genre);
  if (seed !== undefined) params.set("seed", String(seed));

  const res = await fetch(`${API_BASE}/api/pipeline?${params}`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Pipeline failed: ${res.status} ${text}`);
  }

  return res.json();
}

export function getAudioUrl(path: string): string {
  return `${API_BASE}${path}`;
}

export async function generateFromState(
  biomeState: BiomeState,
  durationSeconds: number = 30,
  seed?: number,
  genre: string = "classical",
): Promise<string> {
  const res = await fetch(`${API_BASE}/api/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      biome_state: biomeState,
      duration_seconds: durationSeconds,
      seed: seed ?? Math.floor(Math.random() * 100000),
      genre,
    }),
  });

  if (!res.ok) {
    throw new Error(`Generate failed: ${res.status}`);
  }

  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

export interface SensorReading {
  ph: number;
  h2_ppm: number;
  ch4_ppm: number;
  temp_c: number;
}

export interface SensorResponse {
  ph: number;
  h2: number;
  ch4: number;
  temp: number;
  biome: BiomeState;
  state: string;
  mood: string;
  score: number;
  audio_url: string;
}

export async function sendSensorReading(
  reading: SensorReading
): Promise<SensorResponse> {
  const res = await fetch(`${API_BASE}/api/sensor`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(reading),
  });
  if (!res.ok) throw new Error(`Sensor failed: ${res.status}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// Comprehensive multi-channel analysis
// ---------------------------------------------------------------------------

export interface Disagreement {
  parameter: string;
  channel_a: string;
  channel_b: string;
  value_a: number;
  value_b: number;
  delta: number;
  severity: "low" | "moderate" | "high";
}

export interface ComprehensiveResponse {
  fused_biome_state: BiomeState;
  channel_states: Record<string, BiomeState>;
  channels_used: string[];
  missing_channels: string[];
  channels_count: number;
  overall_confidence: number;
  disagreements: Disagreement[];
  active_instruments: { id: string; name: string; instrument: string; role: string; amplitude: number }[];
  audio_url: string;
  gut_score: number;
  state: string;
  mood: string;
}

export async function runComprehensive(params: {
  file?: File;
  ph?: number;
  temp_c?: number;
  h2_ppm?: number;
  ch4_ppm?: number;
  duration_seconds?: number;
  seed?: number;
  genre?: string;
}): Promise<ComprehensiveResponse> {
  const formData = new FormData();
  if (params.file) formData.append("file", params.file);
  if (params.ph !== undefined) formData.append("ph", String(params.ph));
  if (params.temp_c !== undefined) formData.append("temp_c", String(params.temp_c));
  if (params.h2_ppm !== undefined) formData.append("h2_ppm", String(params.h2_ppm));
  if (params.ch4_ppm !== undefined) formData.append("ch4_ppm", String(params.ch4_ppm));
  formData.append("duration_seconds", String(params.duration_seconds ?? 30));
  if (params.seed !== undefined) formData.append("seed", String(params.seed));
  formData.append("genre", params.genre ?? "classical");

  const res = await fetch(`${API_BASE}/api/comprehensive`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Comprehensive analysis failed: ${res.status} ${text}`);
  }

  return res.json();
}

// ---------------------------------------------------------------------------
// Questionnaire — dietary/lifestyle inputs
// ---------------------------------------------------------------------------

export interface QuestionnaireInput {
  fiber_servings?: number;
  alcohol_units?: number;
  exercise_minutes?: number;
  stress_level?: number;
  sleep_hours?: number;
  duration_seconds?: number;
  seed?: number;
  genre?: string;
}

export interface QuestionnaireResponse {
  biome_state: BiomeState;
  estimated_biomarkers: { ph: number; h2_ppm: number; ch4_ppm: number; temp_c: number };
  state: string;
  mood: string;
  score: number;
  audio_url: string;
  active_instruments: { id: string; name: string; instrument: string; role: string; amplitude: number }[];
}

export async function runQuestionnaire(
  params: QuestionnaireInput,
): Promise<QuestionnaireResponse> {
  const res = await fetch(`${API_BASE}/api/questionnaire`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Questionnaire failed: ${res.status} ${text}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Instruments
// ---------------------------------------------------------------------------

export interface InstrumentInfo {
  id: string;
  name: string;
  instrument: string;
  role: "good" | "bad" | "archaea";
  oscillator: string;
  freq_base: number;
  percussive: boolean;
  sporadic: boolean;
  active: boolean;
  amplitude: number;
}

export interface InstrumentResponse {
  instruments: InstrumentInfo[];
  active_count: number;
  tempo_bpm: number;
  harmonic_richness: number;
  inflammation_detune: number;
}

export async function getInstruments(
  biomeState: BiomeState,
  genre: string = "classical",
): Promise<InstrumentResponse> {
  const res = await fetch(`${API_BASE}/api/instruments`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ biome_state: biomeState, genre }),
  });
  if (!res.ok) throw new Error(`Instruments failed: ${res.status}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// Trajectory prediction
// ---------------------------------------------------------------------------

export interface PredictEvent {
  type: string;
  offset_seconds: number;
}

export interface ParamPrediction {
  mean: number[];
  lower: number[];
  upper: number[];
  std: number[];
}

export interface PredictResponse {
  t_steps: number[];
  predictions: Record<string, ParamPrediction>;
  confidence: number[];
  events_applied: string[];
  n_observations: number;
  instrument_trajectory: Record<string, number[]>;
  audio_url?: string;
}

export async function predictTrajectory(
  biomeState: BiomeState,
  events: PredictEvent[],
  horizonSeconds = 86_400,
  nSteps = 48,
): Promise<PredictResponse> {
  const observations = [{ timestamp: Date.now() / 1000, biome_state: biomeState }];
  const res = await fetch(`${API_BASE}/api/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ horizon_seconds: horizonSeconds, n_steps: nSteps, events, observations }),
  });
  if (!res.ok) throw new Error(`Predict failed: ${res.status}`);
  return res.json();
}

export async function predictAudio(
  biomeState: BiomeState,
  events: PredictEvent[],
  horizonSeconds = 86_400,
  nSteps = 24,
): Promise<PredictResponse> {
  const observations = [{ timestamp: Date.now() / 1000, biome_state: biomeState }];
  const res = await fetch(`${API_BASE}/api/predict/audio`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ horizon_seconds: horizonSeconds, n_steps: nSteps, events, observations }),
  });
  if (!res.ok) throw new Error(`Predict audio failed: ${res.status}`);
  return res.json();
}