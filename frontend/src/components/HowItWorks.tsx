"use client";

import { useState } from "react";

const STEPS = [
  {
    title: "Image Analysis",
    description:
      "We scan your gut endoscopy image for visual features — color, texture, surface shine, and structural detail. These are the same features gastroenterologists look at, extracted using computer vision.",
  },
  {
    title: "Biome Inference",
    description:
      "Published research (SMEAR, HyperKvasir) has shown that what gut tissue looks like correlates with what microbes live there. We use those correlations to estimate 8 biological markers from the image.",
  },
];

const MARKERS = [
  {
    name: "Diversity",
    sound: "Number of voices & harmonic richness",
    detail:
      "A diverse microbiome means many species coexisting — like a full orchestra. Low diversity sounds thin and sparse, like a solo instrument in an empty room.",
    icon: "🎼",
  },
  {
    name: "Inflammation",
    sound: "Distortion & harsh metallic tones",
    detail:
      "Inflamed tissue appears red and swollen. We translate that agitation into sound — the more inflammation, the more the audio distorts and takes on a harsh, grating edge. Think of it like feedback on a guitar amp.",
    icon: "🔥",
  },
  {
    name: "Firmicutes",
    sound: "Deep bass drone",
    detail:
      "Firmicutes are the \"foundation\" bacteria — the largest phylum in a healthy gut. They become the low-frequency bedrock of your composition, a deep sustained hum beneath everything else.",
    icon: "🎵",
  },
  {
    name: "Bacteroidetes",
    sound: "Clear mid-range harmonics",
    detail:
      "These are the metabolic workhorses of your gut. When they're present, you hear warm, clear tones in the middle frequencies — like the body of a cello or a clean piano chord.",
    icon: "🎹",
  },
  {
    name: "Proteobacteria",
    sound: "Dissonance & noise",
    detail:
      "A bloom of Proteobacteria often signals dysbiosis — an imbalanced gut. This translates to clashing intervals, unpredictable noise, and rhythmic irregularity. It's the sound of instability.",
    icon: "⚡",
  },
  {
    name: "Motility",
    sound: "Tempo & rhythm",
    detail:
      "How actively your gut is moving — its peristalsis. High motility means a faster, more rhythmically dense composition. A sluggish gut produces slow, sparse rhythms.",
    icon: "💫",
  },
  {
    name: "Mucosal Integrity",
    sound: "Reverb & space",
    detail:
      "The mucosal barrier protects your gut lining. When it's intact, the sound is tight and defined — like music in a small room. When it's eroded, the reverb opens up into a vast, cavernous echo.",
    icon: "🏛️",
  },
  {
    name: "Metabolic Energy",
    sound: "Volume & dynamics",
    detail:
      "How metabolically active your gut ecosystem is. High energy means louder, punchier sound with sharp note attacks. Low energy sounds quiet and subdued.",
    icon: "⚡",
  },
];

export default function HowItWorks() {
  const [expanded, setExpanded] = useState(false);
  const [activeMarker, setActiveMarker] = useState<number | null>(null);

  return (
    <div className="w-full max-w-2xl mx-auto">
      <button
        onClick={() => setExpanded(!expanded)}
        className="
          w-full text-center font-mono text-[11px] text-muted/50
          hover:text-muted transition-colors duration-300
          py-3 group
        "
      >
        <span className="border-b border-dashed border-muted/20 group-hover:border-muted/40 pb-0.5">
          {expanded ? "Hide" : "How does it work?"}
        </span>
      </button>

      {expanded && (
        <div
          className="mt-4 space-y-8 animate-[fadeIn_0.4s_ease]"
        >
          {/* Pipeline steps */}
          <div className="space-y-4">
            {STEPS.map((step, i) => (
              <div key={i} className="flex gap-3">
                <div className="flex flex-col items-center">
                  <div className="w-5 h-5 rounded-full border border-accent/30 flex items-center justify-center text-[10px] text-accent/60 font-mono">
                    {i + 1}
                  </div>
                  {i < STEPS.length - 1 && (
                    <div className="w-px flex-1 bg-surface-light mt-1" />
                  )}
                </div>
                <div className="pb-4">
                  <h3 className="text-xs text-foreground/80 font-medium mb-1">
                    {step.title}
                  </h3>
                  <p className="text-[11px] text-muted/70 leading-relaxed">
                    {step.description}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {/* Biomarker → Sound mapping */}
          <div>
            <h3 className="text-[10px] uppercase tracking-widest text-muted/40 mb-3">
              From biology to sound
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {MARKERS.map((marker, i) => (
                <button
                  key={i}
                  onClick={() =>
                    setActiveMarker(activeMarker === i ? null : i)
                  }
                  className={`
                    text-left rounded-lg p-3 transition-all duration-300
                    ${
                      activeMarker === i
                        ? "bg-accent/5 border border-accent/20"
                        : "bg-surface/30 border border-transparent hover:bg-surface/50"
                    }
                  `}
                >
                  <div className="flex items-start gap-2">
                    <span className="text-sm mt-0.5">{marker.icon}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-baseline justify-between gap-2">
                        <span className="text-[11px] text-foreground/80 font-medium">
                          {marker.name}
                        </span>
                        <span className="text-[9px] text-accent/50 font-mono truncate">
                          {marker.sound}
                        </span>
                      </div>

                      {activeMarker === i && (
                        <p className="text-[11px] text-muted/60 leading-relaxed mt-2 animate-[fadeIn_0.3s_ease]">
                          {marker.detail}
                        </p>
                      )}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Bottom line */}
          <p className="text-[10px] text-muted/30 text-center leading-relaxed">
            A healthy gut sounds consonant and ambient. A dysbiotic gut sounds harsh and unsettling.
            <br />
            The body becomes the composer.
          </p>
        </div>
      )}
    </div>
  );
}
