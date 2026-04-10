"use client";

import { useState } from "react";
import type { BiomeState } from "@/lib/api";

interface BacteriaGuideProps {
  biomeState: BiomeState;
}

interface Bacterium {
  id: string;
  name: string;
  phylum: string;
  nickname: string;
  biomeKey: keyof BiomeState | null;
  goodDirection: "high" | "low" | null;
  color: string;
  role: string;
  whenHigh: string;
  whenLow: string;
  boostWith: string[];
  reducedBy: string[];
  gutBrainLink: string;
  musicRole: string;
  funFact: string;
}

const BACTERIA: Bacterium[] = [
  {
    id: "firmicutes",
    name: "Firmicutes",
    phylum: "Phylum",
    nickname: "The foundation builders",
    biomeKey: "firmicutes_dominance",
    goodDirection: "high",
    color: "0, 200, 160",
    role: "The largest bacterial phylum in your gut. Includes Lactobacillus, Clostridium, and butyrate-producing species like Faecalibacterium prausnitzii. Primary fermenters of dietary fiber into short-chain fatty acids (SCFAs) — the fuel that powers your colon cells.",
    whenHigh: "Strong SCFA production, good energy for colon cells, healthy fermentation. Butyrate (a key SCFA) strengthens the gut barrier and has anti-inflammatory effects.",
    whenLow: "Reduced butyrate production, weaker gut lining, less protection against pathogens. Associated with IBD, obesity, and metabolic disorders.",
    boostWith: ["Diverse dietary fibers", "Resistant starch (cooked-cooled rice/potatoes)", "Whole grains", "Legumes", "Prebiotics (inulin, FOS)"],
    reducedBy: ["Antibiotics", "High-fat/low-fiber diet", "Stress", "Alcohol"],
    gutBrainLink: "Firmicutes produce butyrate which crosses the blood-brain barrier and supports BDNF (brain-derived neurotrophic factor) — linked to mood, memory, and reduced anxiety.",
    musicRole: "Controls the bass line and foundation instruments. High Firmicutes = deep, warm bass tones underpinning the whole composition.",
    funFact: "Faecalibacterium prausnitzii, a key Firmicutes member, is the single most abundant bacterium in a healthy gut — and one of the first to disappear in Crohn's disease.",
  },
  {
    id: "bacteroidetes",
    name: "Bacteroidetes",
    phylum: "Phylum",
    nickname: "The metabolic workhorses",
    biomeKey: "bacteroidetes_dominance",
    goodDirection: "high",
    color: "91, 155, 213",
    role: "Second-largest phylum, including Bacteroides and Prevotella. Masters of complex carbohydrate breakdown — they carry more carbohydrate-digesting genes than any other gut phylum. Critical for nutrient extraction and immune system education.",
    whenHigh: "Efficient polysaccharide digestion, good immune tolerance, healthy Firmicutes:Bacteroidetes ratio. Associated with leaner body composition and lower inflammation.",
    whenLow: "Reduced complex carbohydrate digestion, altered immune responses. Western diets low in fiber consistently deplete Bacteroidetes.",
    boostWith: ["High-fiber vegetables", "Polyphenol-rich foods (berries, dark chocolate)", "Mediterranean diet", "Fasting periods"],
    reducedBy: ["High-sugar diet", "Ultra-processed foods", "Antibiotic courses", "Sedentary lifestyle"],
    gutBrainLink: "Bacteroides produce GABA precursors and influence tryptophan metabolism — affecting serotonin production. Low Bacteroidetes is associated with depression and anxiety.",
    musicRole: "Drives the mid-frequency harmonic content — melodic clarity and tonal richness. High Bacteroidetes = clear, defined melodic lines.",
    funFact: "Bacteroides thetaiotaomicron can switch between digesting plant polysaccharides and host mucus depending on what's available — a remarkable dietary flexibility.",
  },
  {
    id: "proteobacteria",
    name: "Proteobacteria",
    phylum: "Phylum",
    nickname: "The opportunists",
    biomeKey: "proteobacteria_bloom",
    goodDirection: "low",
    color: "255, 69, 88",
    role: "A phylum that includes E. coli, Salmonella, H. pylori, and Helicobacter. Small amounts are normal and even beneficial. However, blooms — where Proteobacteria outcompete beneficial species — are a hallmark of dysbiosis and inflammation.",
    whenHigh: "Dysbiosis signal. Proteobacteria bloom indicates the gut environment has shifted — lower pH buffer, increased oxygen, or reduced competition from Firmicutes/Bacteroidetes. Associated with IBD, metabolic syndrome, and liver disease.",
    whenLow: "Normal healthy state. A low, stable Proteobacteria presence is part of a balanced microbiome.",
    boostWith: ["Nothing — you want this low"],
    reducedBy: ["Diverse fiber intake", "Probiotic supplementation (L. rhamnosus GG, B. longum)", "Reduced sugar and processed food", "Polyphenols (green tea, resveratrol)"],
    gutBrainLink: "High Proteobacteria produces LPS (lipopolysaccharide) endotoxins that trigger systemic inflammation — linked to neuroinflammation, brain fog, and depressive symptoms.",
    musicRole: "Injects dissonance and noise. High Proteobacteria = dissonant intervals, rhythmic irregularity, FM distortion layers.",
    funFact: "Even E. coli — normally a pathogen concern — has commensal strains that are essential gut residents. It's the ratio and context that matters, not just the species.",
  },
  {
    id: "lactobacillus",
    name: "Lactobacillus",
    phylum: "Firmicutes (genus)",
    nickname: "The probiotic icons",
    biomeKey: null,
    goodDirection: "high",
    color: "0, 229, 160",
    role: "The most studied probiotic genus. Produces lactic acid (lowering gut pH to inhibit pathogens), hydrogen peroxide, and bacteriocins. Found in fermented foods. L. rhamnosus, L. acidophilus, and L. plantarum are the most clinically studied strains.",
    whenHigh: "Acidic, pathogen-resistant gut environment. Strong barrier function. Associated with reduced diarrhea, better lactose digestion, lower UTI risk.",
    whenLow: "Higher pathogen susceptibility, looser gut barrier, more inflammation. Often depleted after antibiotic courses.",
    boostWith: ["Yogurt with live cultures", "Kefir", "Sauerkraut", "Kimchi", "Lactobacillus-specific probiotic supplements"],
    reducedBy: ["Antibiotics (especially broad-spectrum)", "High sugar diet", "Stress", "Alcohol"],
    gutBrainLink: "L. rhamnosus JB-1 produces GABA and has demonstrated reduced anxiety and depression in multiple clinical trials. Often called a 'psychobiotic'.",
    musicRole: "Contributes bright, high-register melodic lines and harmonic shimmer in the granular synthesis layer.",
    funFact: "L. reuteri — found in breast milk — produces a compound called reuterin that is antimicrobial against over 60 pathogens while leaving beneficial bacteria untouched.",
  },
  {
    id: "bifidobacterium",
    name: "Bifidobacterium",
    phylum: "Actinobacteria (genus)",
    nickname: "The diversity anchors",
    biomeKey: null,
    goodDirection: "high",
    color: "175, 140, 220",
    role: "Among the first bacteria to colonise the infant gut, and one of the most beneficial genera across life. Produces acetate and lactate, feeds other bacteria, and directly educates the immune system. B. longum, B. breve, and B. bifidum are key species.",
    whenHigh: "Robust immune system, strong barrier, high diversity ecosystem. Bifidobacterium acts as an 'ecosystem engineer' — its metabolites feed other beneficial species.",
    whenLow: "Reduced immune regulation, associated with allergies, eczema, IBS, and lower overall diversity. Non-secretors (FUT2 gene variant, ~20% of people) naturally have lower Bifidobacterium.",
    boostWith: ["Galactooligosaccharides (GOS) — found in legumes and breast milk", "Inulin", "Lactulose", "B. longum probiotic supplements"],
    reducedBy: ["Caesarean birth (doesn't colonise from vaginal canal)", "Formula feeding vs breastfeeding", "Antibiotics", "Age (naturally declines after 60)"],
    gutBrainLink: "B. longum 1714 reduces cortisol response to stress and improves cognitive performance in clinical trials. One of the strongest psychobiotic candidates currently in research.",
    musicRole: "Drives harmonic complexity and chord density — more Bifidobacterium = more simultaneous voices in the composition.",
    funFact: "Your FUT2 gene determines whether your gut mucosa produces fucosylated sugars that Bifidobacterium feeds on. About 20% of people are 'non-secretors' and have up to half the Bifidobacterium diversity of secretors.",
  },
  {
    id: "akkermansia",
    name: "Akkermansia muciniphila",
    phylum: "Verrucomicrobia (genus)",
    nickname: "The barrier guardian",
    biomeKey: "mucosal_integrity",
    goodDirection: "high",
    color: "245, 166, 35",
    role: "Lives exclusively in the mucus layer of your gut. Feeds on mucin (your gut's protective coating) in a way that paradoxically strengthens it — its metabolites signal the gut to produce more mucus. One of the most exciting targets in microbiome research.",
    whenHigh: "Thick, healthy mucus layer, strong barrier function, better metabolic health. High Akkermansia is associated with leanness, lower diabetes risk, and better response to cancer immunotherapy.",
    whenLow: "Thinner mucus layer, increased gut permeability ('leaky gut'). Associated with obesity, type 2 diabetes, IBD, and neurodegeneration.",
    boostWith: ["Polyphenols — especially pomegranate, cranberry, grape", "Fasting / time-restricted eating", "Omega-3 fatty acids", "Pasteurised Akkermansia supplements (recently approved in EU)"],
    reducedBy: ["High-fat diet", "Antibiotics", "Processed foods", "Sedentary lifestyle"],
    gutBrainLink: "Akkermansia's metabolite propionate crosses the gut-brain axis and influences satiety hormones and dopamine signalling — potentially relevant to food addiction and mood.",
    musicRole: "Controls reverb decay time — representing mucosal integrity as spatial depth. High Akkermansia = tight, defined reverb. Low = cavernous, washed-out.",
    funFact: "Akkermansia comprises just 1–3% of gut bacteria in healthy people, but this tiny fraction has an outsized effect. It's like the keystone species of your gut ecosystem.",
  },
  {
    id: "faecalibacterium",
    name: "Faecalibacterium prausnitzii",
    phylum: "Firmicutes (genus)",
    nickname: "The anti-inflammatory champion",
    biomeKey: "mucosal_integrity",
    goodDirection: "high",
    color: "0, 200, 160",
    role: "The single most abundant bacterium in the healthy human gut and one of the most important. A specialist butyrate producer with powerful anti-inflammatory properties. Its outer membrane proteins directly suppress inflammatory cytokines.",
    whenHigh: "Strong anti-inflammatory activity, healthy gut lining, protection against IBD. F. prausnitzii produces butyrate that feeds colonocytes (colon cells) as their primary energy source.",
    whenLow: "Dramatically reduced in Crohn's disease, ulcerative colitis, and IBS. Low F. prausnitzii is one of the most consistent findings across gut disease research.",
    boostWith: ["Inulin and FOS prebiotics", "Pectin (apples, citrus peel)", "Arabinoxylan (wheat bran)", "Diverse plant fiber"],
    reducedBy: ["Antibiotics", "IBD itself (creates hostile environment)", "Antibiotics", "Low-fiber Western diet"],
    gutBrainLink: "Butyrate from F. prausnitzii maintains the blood-brain barrier integrity and reduces neuroinflammation. Low F. prausnitzii is associated with depression in multiple studies.",
    musicRole: "Contributes to the bass drone layer stability — its presence keeps the foundational tones warm and sustained rather than thin and wavering.",
    funFact: "F. prausnitzii is so oxygen-sensitive it dies within minutes of air exposure — which is why it's nearly impossible to culture in a lab and why it took so long to study.",
  },
  {
    id: "methanobrevibacter",
    name: "Methanobrevibacter smithii",
    phylum: "Archaea (not a bacterium!)",
    nickname: "The methane producer",
    biomeKey: "motility_activity",
    goodDirection: null,
    color: "245, 100, 35",
    role: "Technically an archaeon not a bacterium — a completely different domain of life. Consumes hydrogen produced by bacterial fermentation and produces methane (CH₄). Present in ~30% of people. Its activity dramatically affects gut transit time.",
    whenHigh: "Slower gut transit (constipation-type symptoms), bloating, and altered fermentation dynamics — because it removes hydrogen that other bacteria need. Can dominate in a low-fiber gut.",
    whenLow: "Normal hydrogen levels, more typical transit time. Absence doesn't cause problems but its presence in balance is considered normal.",
    boostWith: ["Nothing specifically — it colonises based on hydrogen availability"],
    reducedBy: ["High-fiber diet (changes fermentation dynamics)", "Probiotic competition", "Some research suggests pomegranate extracts"],
    gutBrainLink: "Methane itself may slow gut-brain signalling via the enteric nervous system, potentially contributing to brain fog and fatigue in people with methane-dominant gut profiles.",
    musicRole: "When dominant, takes over the bass register with heavy drone tones and dramatically slows tempo — representing sluggish motility.",
    funFact: "M. smithii is one of the oldest organisms on Earth — archaea have been around for 3.8 billion years, predating even bacteria. You're hosting something ancient.",
  },
];

export default function BacteriaGuide({ biomeState }: BacteriaGuideProps) {
  const [selected, setSelected] = useState<string | null>(null);
  const selectedBacterium = BACTERIA.find(b => b.id === selected);

  return (
    <div className="flex flex-col gap-5">

      {/* Grid of bacteria cards */}
      <div className="grid grid-cols-2 gap-3">
        {BACTERIA.map((b) => {
          const val = b.biomeKey ? biomeState[b.biomeKey] : null;
          const isActive = selected === b.id;
          const health = val !== null
            ? (b.goodDirection === "high" ? val : b.goodDirection === "low" ? 1 - val : 0.5)
            : 0.5;
          const statusColor = val === null ? b.color
            : health > 0.6 ? "0,240,200"
            : health > 0.35 ? "245,166,35"
            : "255,69,88";

          // Likelihood percentage and meaning
          let likelihood = val !== null ? Math.round(val * 100) : null;
          let meaning = "";
          if (val !== null) {
            if (b.goodDirection === "high") {
              if (val > 0.7) meaning = "Optimal presence";
              else if (val > 0.4) meaning = "Moderate presence";
              else meaning = "Low presence";
            } else if (b.goodDirection === "low") {
              if (val < 0.3) meaning = "Optimal (low)";
              else if (val < 0.6) meaning = "Moderate (watch)";
              else meaning = "High (risk marker)";
            } else {
              meaning = "See details";
            }
          }

          return (
            <button
              key={b.id}
              onClick={() => setSelected(selected === b.id ? null : b.id)}
              style={{
                border: `1px solid ${isActive ? `rgba(${b.color},0.5)` : "rgba(255,255,255,0.06)"}`,
                borderRadius: "6px",
                padding: "12px 14px",
                background: isActive ? `rgba(${b.color},0.07)` : "transparent",
                textAlign: "left",
                cursor: "pointer",
                transition: "all 0.2s",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "7px", marginBottom: "4px" }}>
                <div style={{ width: "5px", height: "5px", borderRadius: "50%", background: `rgb(${statusColor})`, boxShadow: `0 0 4px rgba(${statusColor},0.6)`, flexShrink: 0 }} />
                <span style={{ fontSize: "11px", fontWeight: 500, color: "rgb(200,212,224)", fontFamily: "var(--font-mono)" }}>
                  {b.name}
                </span>
              </div>
              <div style={{ fontSize: "9px", color: "rgba(200,212,224,0.4)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "6px" }}>
                {b.nickname}
              </div>
              {/* Likelihood bar and percentage */}
              {val !== null && (
                <div style={{ marginBottom: 4 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <div style={{ flex: 1, height: "4px", background: "rgba(255,255,255,0.08)", borderRadius: "2px", overflow: "hidden" }}>
                      <div style={{ height: "100%", width: `${val * 100}%`, background: `rgb(${statusColor})`, transition: "width 0.8s ease" }} />
                    </div>
                    <span style={{ fontSize: "10px", color: `rgba(${statusColor},0.85)`, fontFamily: "var(--font-mono)", minWidth: 28, textAlign: "right" }}>{likelihood}%</span>
                  </div>
                  <div style={{ fontSize: "9px", color: "rgba(200,212,224,0.5)", marginTop: 2 }}>{meaning}</div>
                </div>
              )}
              {val === null && (
                <div style={{ fontSize: "9px", color: "rgba(200,212,224,0.25)" }}>tap to learn more</div>
              )}
            </button>
          );
        })}
      </div>

      {/* Detail panel */}
      {selectedBacterium && (
        <div
          style={{
            border: `1px solid rgba(${selectedBacterium.color},0.2)`,
            borderRadius: "8px",
            padding: "20px",
            background: `rgba(${selectedBacterium.color},0.04)`,
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "14px" }}>
            <div>
              <div style={{ fontSize: "9px", letterSpacing: "0.15em", textTransform: "uppercase", color: `rgba(${selectedBacterium.color},0.6)`, marginBottom: "4px" }}>
                {selectedBacterium.phylum}
              </div>
              <div style={{ fontSize: "16px", fontWeight: 500, color: "rgb(200,212,224)", fontFamily: "var(--font-mono)" }}>
                {selectedBacterium.name}
              </div>
              <div style={{ fontSize: "11px", color: `rgba(${selectedBacterium.color},0.7)`, marginTop: "2px" }}>
                {selectedBacterium.nickname}
              </div>
            </div>
            <button
              onClick={() => setSelected(null)}
              style={{ fontSize: "11px", color: "rgba(200,212,224,0.3)", background: "none", border: "none", cursor: "pointer", fontFamily: "var(--font-mono)" }}
            >
              close
            </button>
          </div>

          <DetailSection label="What it does" color={selectedBacterium.color}>
            {selectedBacterium.role}
          </DetailSection>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", margin: "12px 0" }}>
            <DetailSection label="When levels are high" color="0,240,200">
              {selectedBacterium.whenHigh}
            </DetailSection>
            <DetailSection label="When levels are low" color="255,69,88">
              {selectedBacterium.whenLow}
            </DetailSection>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", margin: "12px 0" }}>
            <div>
              <div style={{ fontSize: "9px", letterSpacing: "0.15em", textTransform: "uppercase", color: "rgba(0,240,200,0.5)", marginBottom: "6px" }}>
                Boost with
              </div>
              <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                {selectedBacterium.boostWith.map((item, i) => (
                  <li key={i} style={{ fontSize: "11px", color: "rgba(200,212,224,0.6)", lineHeight: 1.7, display: "flex", gap: "6px" }}>
                    <span style={{ color: "rgba(0,240,200,0.4)", flexShrink: 0 }}>+</span>{item}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <div style={{ fontSize: "9px", letterSpacing: "0.15em", textTransform: "uppercase", color: "rgba(255,69,88,0.5)", marginBottom: "6px" }}>
                Reduced by
              </div>
              <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                {selectedBacterium.reducedBy.map((item, i) => (
                  <li key={i} style={{ fontSize: "11px", color: "rgba(200,212,224,0.6)", lineHeight: 1.7, display: "flex", gap: "6px" }}>
                    <span style={{ color: "rgba(255,69,88,0.4)", flexShrink: 0 }}>−</span>{item}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <DetailSection label="Gut-brain axis connection" color="175,140,220">
            {selectedBacterium.gutBrainLink}
          </DetailSection>

          <DetailSection label="In your music" color={selectedBacterium.color} style={{ marginTop: "10px" }}>
            {selectedBacterium.musicRole}
          </DetailSection>

          <div style={{ marginTop: "12px", padding: "10px 12px", background: "rgba(255,255,255,0.03)", borderRadius: "5px", borderLeft: `2px solid rgba(${selectedBacterium.color},0.3)` }}>
            <div style={{ fontSize: "9px", letterSpacing: "0.15em", textTransform: "uppercase", color: `rgba(${selectedBacterium.color},0.5)`, marginBottom: "4px" }}>
              Fun fact
            </div>
            <p style={{ fontSize: "11px", color: "rgba(200,212,224,0.55)", lineHeight: 1.6, fontStyle: "italic" }}>
              {selectedBacterium.funFact}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

function DetailSection({ label, color, children, style }: {
  label: string; color: string; children: React.ReactNode; style?: React.CSSProperties;
}) {
  return (
    <div style={style}>
      <div style={{ fontSize: "9px", letterSpacing: "0.15em", textTransform: "uppercase", color: `rgba(${color},0.5)`, marginBottom: "5px" }}>
        {label}
      </div>
      <p style={{ fontSize: "11px", color: "rgba(200,212,224,0.6)", lineHeight: 1.65 }}>
        {children}
      </p>
    </div>
  );
}
