# BIOME SOUND — Gut Microbiome Sonification Engine

## Overview

A web application that takes endoscopy/gut imagery as input, analyzes visual features to infer microbiome states, and generates downloadable audio compositions from that data. The body becomes the composer.

The scientific basis: published research (SMEAR, HyperKvasir) has established statistical correlations between visual features of gut tissue (color, texture, moisture, structure) and microbiome composition (bacterial diversity, genera presence, inflammatory state). This project uses those correlations as an inference bridge to translate visual gut data into sound.

This is an art/science project, not a diagnostic tool. The inference layer should be scientifically grounded but the priority is musicality and audience-facing polish.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     FRONTEND (Next.js)                  │
│                                                         │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐ │
│  │  Upload   │  │  Gut Image   │  │  Audio Player +   │ │
│  │  Zone     │→ │  Viewer      │→ │  Waveform Display │ │
│  └──────────┘  └──────────────┘  └───────────────────┘ │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Biome Dashboard                                  │   │
│  │  (inferred parameters displayed as visual meters) │   │
│  └──────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────┘
                         │ API calls
┌────────────────────────▼────────────────────────────────┐
│                   BACKEND (FastAPI + Python)             │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │  CV Feature   │→ │  Inference   │→ │  Sonification │ │
│  │  Extraction   │  │  Bridge      │  │  Engine       │ │
│  │  (OpenCV)     │  │  (SMEAR-     │  │  (librosa,    │ │
│  │              │  │  informed)   │  │  pydub,       │ │
│  │              │  │              │  │  scipy)       │ │
│  └──────────────┘  └──────────────┘  └───────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## Tech Stack

### Frontend
- **Next.js 14+ (App Router)** with TypeScript
- **Tailwind CSS** — dark, minimal, cinematic aesthetic (think medical imaging console)
- **wavesurfer.js** — for audio waveform visualization
- No component library — custom components for the cinematic feel

### Backend
- **FastAPI** (Python)
- **OpenCV** — image/video frame feature extraction
- **NumPy / SciPy** — signal processing, normalization
- **librosa** — audio synthesis, spectral manipulation
- **pydub** — audio export (WAV, MP3)
- **Pillow** — image preprocessing

---

## Core Pipeline (Backend Detail)

### Stage 1: Visual Feature Extraction (`/api/analyze`)

Accept uploaded image(s) or video file. For video, extract frames at configurable interval (default 1 per second).

For each frame, extract these features using OpenCV:

```python
features = {
    # Color (work in HSV space, more biologically meaningful than RGB)
    "dominant_hue": float,          # 0.0-1.0 — maps to mucosal color state
    "saturation_mean": float,       # 0.0-1.0 — tissue vitality
    "value_mean": float,            # 0.0-1.0 — brightness/pallor
    "color_variance": float,        # 0.0-1.0 — heterogeneity of tissue
    "redness_ratio": float,         # 0.0-1.0 — inflammation proxy

    # Texture (Gabor filters + GLCM)
    "texture_energy": float,        # 0.0-1.0 — structural complexity
    "texture_entropy": float,       # 0.0-1.0 — randomness/disorder
    "edge_density": float,          # 0.0-1.0 — amount of structural detail

    # Surface
    "specular_ratio": float,        # 0.0-1.0 — wetness/moisture proxy
    "brightness_variance": float,   # 0.0-1.0 — patchy vs uniform (tissue heterogeneity)

    # Motion (video only)
    "motion_magnitude": float,      # 0.0-1.0 — peristalsis / movement speed
    "motion_direction_variance": float  # 0.0-1.0 — chaotic vs smooth movement
}
```

### Stage 2: Inference Bridge (`/api/infer`)

Map visual features → estimated biome parameters. This is a heuristic mapping layer based on published SMEAR correlations, NOT a trained ML model (yet). The mapping config should be stored in a JSON file so it can be tuned without code changes.

```python
biome_state = {
    "diversity_index": float,         # 0.0-1.0 — overall microbial diversity
    "inflammation_score": float,      # 0.0-1.0 — inflammatory state
    "firmicutes_dominance": float,    # 0.0-1.0 — Firmicutes presence estimate
    "bacteroidetes_dominance": float, # 0.0-1.0 — Bacteroidetes presence estimate
    "proteobacteria_bloom": float,    # 0.0-1.0 — Proteobacteria (often pathogenic)
    "motility_activity": float,       # 0.0-1.0 — gut movement/peristalsis
    "mucosal_integrity": float,       # 0.0-1.0 — tissue health
    "metabolic_energy": float,        # 0.0-1.0 — inferred metabolic activity
}
```

**Inference mapping logic (configurable via `mapping_config.json`):**

```
diversity_index = weighted_average(texture_energy * 0.4, color_variance * 0.3, edge_density * 0.3)
inflammation_score = weighted_average(redness_ratio * 0.6, saturation_mean * 0.2, specular_ratio * 0.2)
firmicutes_dominance = derived from texture patterns (high texture + dark = Firmicutes-dominant)
bacteroidetes_dominance = derived from mid-range color + moderate texture
proteobacteria_bloom = high redness + high edge density + low texture regularity
motility_activity = motion_magnitude (video) or texture_entropy (image fallback)
mucosal_integrity = inverse(specular_ratio * 0.4 + brightness_variance * 0.3 + inflammation_score * 0.3)
metabolic_energy = saturation_mean * 0.5 + texture_energy * 0.3 + (1 - specular_ratio) * 0.2
```

### Stage 3: Sonification Engine (`/api/generate`)

Takes the biome_state (either from a single image or a time-series from video frames) and generates a WAV audio file.

**Mapping: Biome Parameters → Musical Parameters**

| Biome Parameter | Musical Target | Rationale |
|---|---|---|
| `diversity_index` | Number of simultaneous voices / harmonic complexity / chord density | High diversity = rich ecosystem = rich sound |
| `inflammation_score` | Distortion amount, filter resonance, high-frequency energy | Inflammation = agitation, harshness |
| `firmicutes_dominance` | Low-frequency weight (bass), sustained tones | Firmicutes = the "foundation" phylum |
| `bacteroidetes_dominance` | Mid-frequency harmonic content, tonal clarity | Bacteroidetes = metabolic workhorses |
| `proteobacteria_bloom` | Dissonant intervals, noise injection, rhythmic irregularity | Proteobacteria blooms = dysbiosis = instability |
| `motility_activity` | Tempo, rhythmic density, note attack speed | Movement = rhythm |
| `mucosal_integrity` | Reverb decay time (healthy = tight, eroded = cavernous), sustain | Intact barrier = defined space |
| `metabolic_energy` | Overall amplitude, dynamic range, envelope attack sharpness | Energy = loudness and punch |

**Sound design approach — let the data determine the genre:**

- High diversity + low inflammation + high integrity → **ambient/tonal/consonant** (healthy gut sounds beautiful)
- Low diversity + high inflammation + proteobacteria bloom → **harsh/glitchy/dissonant** (dysbiosis sounds unsettling)
- High motility + high metabolic energy → **rhythmic/percussive** (active gut sounds driven)
- Low everything → **sparse/hollow/drone** (atrophic gut sounds empty)

**Synthesis techniques to use:**
- Additive synthesis (sine partials, each voice = a "genus")
- Granular synthesis (for texture layers)
- FM synthesis (for timbral complexity driven by inflammation)
- Filtered noise (for surface/moisture textures)
- Reverb/delay as spatial parameters driven by mucosal_integrity

**For video input (time-series):**
The biome parameters change per frame, creating an evolving composition. Crossfade between states. The audio clip duration should match the video duration (or a configurable multiplier, e.g., 10 seconds of video = 60 seconds of audio).

**For single image input:**
Generate a 30-60 second composition that represents the "state" captured in that single image. Use slow modulation and slight randomization to keep it evolving rather than static.

**Output:** WAV file (44100 Hz, 16-bit). Also return the biome_state JSON so the frontend can display it.

---

## Frontend Detail

### Visual Design Language
- **Background:** near-black (#0A0A0F) with very subtle dark blue/purple undertone
- **Accent color:** teal/cyan (#00F0FF) for active states, data points, waveform
- **Secondary accent:** deep red (#FF2D2D) for inflammation-related displays
- **Text:** light gray (#C8C8D0), monospace for data, sans-serif for headings
- **Aesthetic:** think medical imaging workstation meets Blade Runner — dark, precise, slightly ominous, beautiful
- **Typography:** JetBrains Mono (data), Inter (UI)
- **Animations:** subtle, smooth — slow pulses, not flashy. Bio-organic movement.
- **No borders or boxes** — use light/shadow and spacing to define regions

### Pages / Views

#### 1. Landing / Upload (`/`)
- Full-screen dark background
- Project title "BIOME SOUND" in large, minimal type
- One-line description: "Your gut composes the music."
- Subtle animated background — slow-moving organic particle system or fluid simulation (very dim, atmospheric)
- Upload zone — drag-and-drop area, accepts images (jpg, png, tiff) and video (mp4, mov)
- When file is dropped, transition to the Processing view

#### 2. Processing View (`/process`)
- Shows the uploaded gut image(s) or video thumbnail on the left
- Animated progress indicator — not a spinner, something organic (expanding rings, pulsing dot grid)
- Three-phase progress: "Extracting visual features..." → "Inferring biome state..." → "Composing audio..."
- Each phase has a subtle animation change

#### 3. Results View (`/result`)
This is the main performance-ready screen. Laid out as a cinematic dashboard.

**Left panel (40%):** The gut image/video displayed large. If video, it plays in sync with the audio. Subtle scan-line or imaging overlay effect to reinforce the medical imaging aesthetic.

**Right panel (60%):**

- **Biome State Display** — the 8 biome parameters shown as elegant horizontal meters or radial gauges. Animate them smoothly. Use teal for healthy ranges, shift toward red for inflammatory markers. Each parameter labeled with its name and value.

- **Audio Waveform** — wavesurfer.js waveform in teal/cyan on the dark background. Shows the full generated audio clip. Playhead visible during playback.

- **Play/Pause button** — minimal, centered below waveform

- **Download button** — "Download WAV" — prominent but not garish

- **"Generate Again"** — option to re-generate with slightly different randomization seed

- **Optional: Parameter Adjustment** — small sliders that let the user manually nudge biome parameters and re-generate. This is a stretch goal but would add interactivity.

---

## API Endpoints

```
POST /api/analyze
  Input: image file or video file (multipart form upload)
  Output: { features: [...], frames_analyzed: int }

POST /api/infer
  Input: { features: [...] }
  Output: { biome_state: {...} }

POST /api/generate
  Input: { biome_state: {...}, duration_seconds: int, seed: int }
  Output: WAV file (binary response)

POST /api/pipeline
  Input: image/video file upload + optional params (duration, seed)
  Output: { biome_state: {...}, audio_url: string, features: [...] }
  (This is the all-in-one endpoint the frontend primarily calls)
```

---

## File Structure

```
biome-sound/
├── frontend/
│   ├── app/
│   │   ├── page.tsx              # Landing / Upload
│   │   ├── process/page.tsx      # Processing view
│   │   ├── result/page.tsx       # Results dashboard
│   │   ├── layout.tsx            # Dark theme layout
│   │   └── globals.css           # Tailwind + custom styles
│   ├── components/
│   │   ├── UploadZone.tsx        # Drag-and-drop upload
│   │   ├── BiomeDashboard.tsx    # 8-parameter gauge display
│   │   ├── AudioPlayer.tsx       # Waveform + playback controls
│   │   ├── GutViewer.tsx         # Image/video display with overlay
│   │   ├── ProcessingAnimation.tsx
│   │   └── ParticleBackground.tsx # Subtle landing page bg
│   ├── lib/
│   │   └── api.ts                # API client functions
│   ├── tailwind.config.ts
│   ├── next.config.js
│   └── package.json
├── backend/
│   ├── main.py                   # FastAPI app, route definitions
│   ├── feature_extraction.py     # OpenCV visual feature pipeline
│   ├── inference.py              # SMEAR-informed biome state inference
│   ├── sonification.py           # Audio generation engine
│   ├── mapping_config.json       # Tunable inference + sonification mappings
│   ├── requirements.txt
│   └── tests/
│       ├── test_features.py
│       ├── test_inference.py
│       └── test_sonification.py
├── data/
│   └── sample_images/            # A few test endoscopy images for development
├── README.md
└── docker-compose.yml            # Optional: containerized dev setup
```

---

## Mapping Config (`mapping_config.json`)

This file controls both the inference layer and the sonification layer. It should be the single source of truth for all mappings so that artistic tuning doesn't require code changes.

```json
{
  "inference": {
    "diversity_index": {
      "sources": {
        "texture_energy": 0.4,
        "color_variance": 0.3,
        "edge_density": 0.3
      }
    },
    "inflammation_score": {
      "sources": {
        "redness_ratio": 0.6,
        "saturation_mean": 0.2,
        "specular_ratio": 0.2
      }
    }
  },
  "sonification": {
    "diversity_index": {
      "target": "voice_count",
      "range": [1, 8],
      "curve": "exponential"
    },
    "inflammation_score": {
      "target": "distortion_amount",
      "range": [0.0, 0.8],
      "curve": "linear"
    }
  },
  "scales": {
    "healthy": ["C3", "E3", "G3", "B3", "D4", "F#4", "A4"],
    "dysbiotic": ["C3", "Db3", "E3", "Gb3", "Ab3", "B3", "D4"],
    "atrophic": ["C3", "F3", "G3", "C4"]
  }
}
```

---

## Development Phases

### Phase 1: Backend Pipeline (Week 1)
- [ ] Feature extraction from single image (OpenCV)
- [ ] Inference bridge with mapping_config.json
- [ ] Basic sonification engine — additive synthesis, generate a 30-sec WAV from biome_state
- [ ] `/api/pipeline` endpoint working end-to-end
- [ ] Test with sample endoscopy images

### Phase 2: Frontend Shell (Week 2)
- [ ] Next.js app with dark theme, landing page, upload zone
- [ ] Processing view with progress states
- [ ] Results view with BiomeDashboard (8 gauges) + AudioPlayer (wavesurfer.js)
- [ ] Connect to backend API

### Phase 3: Sound Design Refinement (Week 3)
- [ ] Add granular synthesis layer
- [ ] Add FM synthesis layer for inflammation timbres
- [ ] Add filtered noise layer for surface textures
- [ ] Implement scale/mode selection based on overall biome state
- [ ] Video input support (frame extraction, time-series composition)
- [ ] Crossfading between biome states over time

### Phase 4: Polish (Week 4)
- [ ] Landing page particle/fluid background animation
- [ ] Smooth transitions between views
- [ ] Gut image viewer with scan-line overlay effect
- [ ] BiomeDashboard animation polish (smooth gauge movements)
- [ ] Download WAV button
- [ ] Optional: parameter adjustment sliders for re-generation
- [ ] Mobile responsive (at minimum, results view should look good on phone for sharing)

---

## Key Design Principles

1. **The data leads.** The sound should feel like it *emerges from* the imagery, not like it's been arbitrarily attached. Every mapping should have a defensible rationale.

2. **Healthy guts sound beautiful.** This is an artistic choice with real implications — if someone shares their gut sonification and it sounds gorgeous, that's a positive, affirming experience. Dysbiosis should sound unsettling but still musical, never ugly or punishing.

3. **Cinematic restraint.** The UI should feel like a high-end medical imaging console. No gratuitous animation, no bright colors, no clutter. Let the gut imagery and the sound be the stars. Everything else recedes.

4. **Configurable, not hardcoded.** All mappings live in `mapping_config.json`. The artistic tuning of this project IS the project — the config file is the instrument.

5. **Scientifically grounded, artistically free.** Cite the SMEAR research and the visual-microbiome correlations. Don't claim clinical accuracy. The inference layer is an artistic interpretation anchored in real science.

---

## References

- SMEAR: Smartphone Microbiome Evaluation and Analysis in Rapid-time (Nature Scientific Reports, 2025)
- HyperKvasir dataset: https://datasets.simula.no/hyper-kvasir/
- Photoacoustic identification of gut microbes (Optics Letters, 2017)
- Decoding gut microbiota by imaging analysis of fecal samples (iScience/PMC, 2021)
- Human Microbiome Project data: https://hmpdacc.org/

---

## Notes for Claude Code

- Start with the backend. Get `/api/pipeline` working with a single test image before touching frontend.
- For sonification, start simple: additive synthesis with sine waves. Get the mapping working first. Layer in granular/FM/noise after the pipeline is proven.
- The `mapping_config.json` is critical infrastructure. Build the system around it from day one.
- Use Python's `soundfile` library for WAV output (cleaner than pydub for synthesis).
- For video frame extraction, use OpenCV's VideoCapture. Extract 1 frame/sec by default.
- Frontend should poll or use SSE for processing progress (the generate step could take 5-15 seconds).
- The aesthetic matters as much as the functionality. This is a performance piece. If it looks like a hackathon project, it fails.
