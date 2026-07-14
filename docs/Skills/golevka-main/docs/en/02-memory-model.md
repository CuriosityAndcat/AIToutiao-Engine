> 🌏 **English (current)** · [简体中文](../02-memory-model.md)

# 02 · The Seven-Layer Memory Model (L0–L6)

A digital life's memory is not one bucket. Dumping everything into a single vector store is the most common engineering mistake in this field. A century of memory research in cognitive science offers a layering you can borrow directly.

```text
── State / storage (retrievable, correctable) ──
L0 Raw evidence      journal/essay originals, immutable forever
L1 Episodic memory   autobiographical events with time & place: "at the 2014 sports meet I finished second to last"
L2 Semantic facts    de-contextualized facts & concepts: "my bachelor's degree took four years"
L3 Procedure & style how they talk, write, habits of thought (tacit — hardest to capture)
L4 Values & judgment value rankings, choice strategies — the "judgment function"
L5 Self-narrative    the integrated story of "who I am"
── Process / plasticity (a fundamentally different kind) ──
L6 Autonomous learning  the mechanism of distilling new principles from lived experience and revising the self-model
```

## State vs. process: the most important line

L0–L5 are **state** (what is stored); L6 is **process** (how state changes). Classifying "autonomous learning" as another memory layer alongside the others is a category error — like classifying "the librarian" as a kind of "book."

This line yields scientific definitions for the two stages:

- **Stage One (high-fidelity reconstruction) = getting L0–L5 to high fidelity.** Today's technology suffices: L0–L2 by retrieval (full-text indexing is enough; keep parent-document links for context), L3–L5 approximated by a persona profile (prompt). The calibration period polishes exactly L3–L5.
- **Stage Two (the fork) = L6 coming online.** What makes a digital life "fork" rather than "accumulate more memory" is precisely this: **it begins forming and revising its own principles from its own experience**, instead of only retrieving yours. Feeding memory to the present ≠ the fork; the fork is the birth of L6.

**The honest boundary**: today's large-model weights are frozen; "correction" is you editing its memory state from the outside, not it learning. A real L6 has only two roads: fine-tuning (true plasticity), or a functional approximation — a persistent "experience → reflection → principle" record it maintains itself. Knowing that you are currently doing the former (a high-fidelity L0–L5 simulation) is how this project stays honest.

## Engineering notes per layer

**L0 raw evidence**: originals are never edited, never deleted. Every upper layer can be rebuilt; L0 alone is a non-renewable resource.

**L1 vs. L2 must be separated** (Tulving's episodic/semantic distinction — different brain systems): episodic memories deform with each retelling, so multiple interpretations of one event may coexist; semantic facts demand exact consistency, so errors need a "correction" mechanism that overrides. Tag each memory `episodic / factual`; retrieval and correction strategy differ by type.

**L3–L5 are tacit knowledge**: they live between the lines of the corpus and cannot be extracted by "asking the person to write a self-description" (people cannot introspectively report how they do what they do). Two things extract them: a large first-person corpus (style seeps out on its own) + the sustained polishing of the [calibration loop](03-calibration.md).

**Dual timestamps** (from reconsolidation research — every act of recall rewrites the memory): each memory carries `date` (when the event happened) and `written_at` (when it was written down). The same event interpreted at 25 and at 31 should be stored separately — never merged, never "newest wins."

**Knowledge cutoff**: at any moment the digital life has an explicit "knows up to which day." This is not just an engineering constraint but a rhythm instrument for raising: you can start it as your 25-year-old self and let it grow up in chapters.

## Two supporting frameworks from cognitive science

- **Complementary Learning Systems (CLS)**: the brain learns with two systems — hippocampus (fast, episodic, one-shot) + neocortex (slow, statistical, gradually consolidating). Mapped to the project: **inherited memory** (your historical corpus — the slow system's stable foundation) and **lived memory** (its experiences after it starts) must be kept in separate buckets. Hard scientific backing for the inherited-vs-lived boundary — and the foundation for a future L6.
- **Predictive processing**: a personality = a generative model with priors; every "not like me" you mark in calibration = a prediction-error signal. The ledger collects the error stream — today it feeds you; one day it feeds L6.

Next: [03 · The Calibration Loop](03-calibration.md)
