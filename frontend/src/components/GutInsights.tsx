"use client";

import { useMemo } from "react";
import type { BiomeState } from "@/lib/api";

interface GutInsightsProps {
  biomeState: BiomeState;
  gutScore: number;
  mood: string;
  gutStateLabel: string;
}

const MOOD_DESCRIPTIONS: Record<string, { desc: string; scale: string; instruments: string }> = {
  peak_diversity: {
    desc: "Maximum fiber fermentation. Multiple bacterial phyla active simultaneously.",
    scale: "Lydian dominant — complex jazz tonality, bright and alive",
    instruments: "Full 6–8 instrument ensemble: layered strings, percussion, piano, melodic lead",
  },
  healthy: {
    desc: "Balanced pH, active H₂ fermentation. Bacteroides and Bifidobacterium thriving.",
    scale: "Lydian — bright, open, warm",
    instruments: "Acoustic bass, guitar, piano, light percussion and melodic lead",
  },
  fasted: {
    desc: "Low fermentation substrate. Microbiome quiet but not distressed — underfed.",
    scale: "Dorian — calm, contemplative, slightly melancholic",
    instruments: "Single acoustic guitar or piano. Sparse, spacious texture",
  },
  methanogen: {
    desc: "Methanobrevibacter smithii consuming hydrogen. Slow motility detected.",
    scale: "Phrygian — dark, low, resolves downward",
    instruments: "Sustained bass drone, cello-like tones. Very slow tempo",
  },
  dysbiosis: {
    desc: "Beneficial bacteria activity crashing. pH disruption — possible sugar overload.",
    scale: "Phrygian dominant — tense, unstable, unresolved",
    instruments: "Instruments drop out one by one. Dissonant intervals emerge",
  },
  inflamed: {
    desc: "Active mucosal inflammation. Proteobacteria blooming, beneficial genera depleted.",
    scale: "Locrian — the most dissonant diatonic mode. Every note feels unstable",
    instruments: "Distorted FM synthesis, high-frequency noise, irregular rhythm",
  },
};

interface Tip {
  priority: "high" | "medium" | "low";
  category: string;
  action: string;
  why: string;
}

function generateTips(b: BiomeState, score: number): Tip[] {
  const tips: Tip[] = [];

  if (b.inflammation_score > 0.5) {
    tips.push({
      priority: "high",
      category: "Reduce inflammation",
      action: "Cut ultra-processed foods, refined sugar, and alcohol for 48–72 hours",
      why: "Your inflammation signal is elevated — these are the fastest dietary levers to pull",
    });
    tips.push({
      priority: "high",
      category: "Anti-inflammatory foods",
      action: "Add oily fish, walnuts, turmeric, and dark leafy greens today",
      why: "Omega-3s and polyphenols directly suppress the inflammatory pathways your sensor is detecting",
    });
  }

  if (b.diversity_index < 0.4) {
    tips.push({
      priority: "high",
      category: "Boost diversity",
      action: "Eat 30 different plant foods this week — every variety counts",
      why: "Low diversity is your biggest signal right now. Different fibers feed different bacterial species",
    });
    tips.push({
      priority: "medium",
      category: "Add fermented foods",
      action: "Include kimchi, kefir, sauerkraut, or plain yogurt with live cultures daily",
      why: "Fermented foods directly seed your gut with Lactobacillus and Bifidobacterium strains",
    });
  }

  if (b.motility_activity < 0.3) {
    tips.push({
      priority: "medium",
      category: "Improve motility",
      action: "20-minute walk after meals, and increase water intake to 2.5L/day",
      why: "Low motility signal — movement and hydration are the two most effective non-dietary interventions",
    });
    tips.push({
      priority: "medium",
      category: "Reduce methane producers",
      action: "Try intermittent fasting (14:10) for a few days to reset transit time",
      why: "High methanogen activity correlates with slower transit — a fasting window can help recalibrate",
    });
  }

  if (b.mucosal_integrity < 0.5) {
    tips.push({
      priority: "high",
      category: "Repair gut lining",
      action: "Prioritise zinc, L-glutamine, and collagen-rich foods (bone broth, slow-cooked meat)",
      why: "Your mucosal integrity score suggests barrier disruption — these nutrients directly support tight junction repair",
    });
  }

  if (b.bacteroidetes_dominance < 0.3) {
    tips.push({
      priority: "medium",
      category: "Feed Bacteroidetes",
      action: "Eat more inulin-rich foods: garlic, onions, leeks, asparagus, chicory root",
      why: "Bacteroidetes are your primary metabolic workhorses and they're currently underrepresented",
    });
  }

  if (b.proteobacteria_bloom > 0.5) {
    tips.push({
      priority: "high",
      category: "Control dysbiosis",
      action: "Avoid antibiotics if possible and add probiotic supplementation (Lactobacillus rhamnosus GG)",
      why: "Proteobacteria bloom is a dysbiosis marker — probiotics compete directly with these opportunistic species",
    });
  }

  if (b.metabolic_energy < 0.4 && b.inflammation_score < 0.3) {
    tips.push({
      priority: "low",
      category: "Boost metabolic activity",
      action: "Add resistant starch: cooked-and-cooled rice or potatoes, unripe banana, lentils",
      why: "Your metabolic energy is low despite low inflammation — more substrate will activate your dormant fermenters",
    });
  }

  if (score > 75) {
    tips.push({
      priority: "low",
      category: "Maintain your score",
      action: "Keep up the fiber diversity and fermented foods — your gut is thriving",
      why: "High diversity, low inflammation, good integrity. Focus on consistency rather than change",
    });
  }

  return tips.slice(0, 4);
}

const PRIORITY_STYLES = {
  high:   { dot: "#FF4558", label: "Priority",  bg: "rgba(255,69,88,0.06)",   border: "rgba(255,69,88,0.15)" },
  medium: { dot: "#F5A623", label: "Suggested", bg: "rgba(245,166,35,0.06)",  border: "rgba(245,166,35,0.15)" },
  low:    { dot: "#00F0C8", label: "Maintain",  bg: "rgba(0,240,200,0.04)",   border: "rgba(0,240,200,0.10)" },
};

export default function GutInsights({ biomeState, gutScore, mood, gutStateLabel }: GutInsightsProps) {
  const tips = useMemo(() => generateTips(biomeState, gutScore), [biomeState, gutScore]);
  const moodInfo = MOOD_DESCRIPTIONS[gutStateLabel] || MOOD_DESCRIPTIONS["healthy"];

  return (
    <div className="flex flex-col gap-6">

      {/* Music mood description */}
      <div
        style={{
          border: "1px solid rgba(0,240,200,0.15)",
          borderRadius: "6px",
          padding: "18px 20px",
          background: "rgba(0,240,200,0.03)",
        }}
      >
        <p style={{ fontSize: "9px", letterSpacing: "0.18em", textTransform: "uppercase", color: "rgba(200,212,224,0.4)", marginBottom: "8px" }}>
          What you&apos;re hearing
        </p>
        <p style={{ fontSize: "13px", color: "rgb(200,212,224)", marginBottom: "8px", lineHeight: 1.6 }}>
          {moodInfo.desc}
        </p>
        <div style={{ fontSize: "10px", color: "rgba(200,212,224,0.5)", lineHeight: 1.7 }}>
          <span style={{ color: "rgba(0,240,200,0.7)" }}>Scale: </span>{moodInfo.scale}<br />
          <span style={{ color: "rgba(0,240,200,0.7)" }}>Sound: </span>{moodInfo.instruments}
        </div>
      </div>

      {/* Tips */}
      <div>
        <p style={{ fontSize: "9px", letterSpacing: "0.18em", textTransform: "uppercase", color: "rgba(200,212,224,0.4)", marginBottom: "14px" }}>
          How to improve your score
        </p>
        <div className="flex flex-col gap-3">
          {tips.map((tip, i) => {
            const s = PRIORITY_STYLES[tip.priority];
            return (
              <div
                key={i}
                style={{
                  border: `1px solid ${s.border}`,
                  borderRadius: "6px",
                  padding: "14px 16px",
                  background: s.bg,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
                  <div style={{ width: "5px", height: "5px", borderRadius: "50%", background: s.dot, boxShadow: `0 0 4px ${s.dot}`, flexShrink: 0 }} />
                  <span style={{ fontSize: "9px", letterSpacing: "0.12em", textTransform: "uppercase", color: s.dot, opacity: 0.8 }}>
                    {s.label}
                  </span>
                  <span style={{ fontSize: "9px", letterSpacing: "0.12em", textTransform: "uppercase", color: "rgba(200,212,224,0.35)", marginLeft: "4px" }}>
                    {tip.category}
                  </span>
                </div>
                <p style={{ fontSize: "12px", color: "rgb(200,212,224)", marginBottom: "4px", fontWeight: 500 }}>
                  {tip.action}
                </p>
                <p style={{ fontSize: "11px", color: "rgba(200,212,224,0.45)", lineHeight: 1.5 }}>
                  {tip.why}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
