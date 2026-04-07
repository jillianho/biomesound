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
  seed?: number
): Promise<PipelineResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const params = new URLSearchParams();
  params.set("duration_seconds", String(durationSeconds));
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
  seed?: number
): Promise<string> {
  const res = await fetch(`${API_BASE}/api/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      biome_state: biomeState,
      duration_seconds: durationSeconds,
      seed: seed ?? Math.floor(Math.random() * 100000),
    }),
  });

  if (!res.ok) {
    throw new Error(`Generate failed: ${res.status}`);
  }

  const blob = await res.blob();
  return URL.createObjectURL(blob);
}
