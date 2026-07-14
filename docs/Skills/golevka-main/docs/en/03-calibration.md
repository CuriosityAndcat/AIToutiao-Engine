> 🌏 **English (current)** · [简体中文](../03-calibration.md)

# 03 · The Calibration Loop

When the corpus is fed, the real raising begins. The calibration loop is the heart of this methodology and what separates it from every "digital twin product": **a twin is delivered; a life is calibrated.**

## The basic loop: one-way calibration

```text
You ask → it answers → you rate → ledger → (if needed) correction/backfill → rebuild corpus → more like you
```

- **Three ratings: like me / not like me / better than I would have.** The third is essential — it takes "fork, not backup" seriously: some answers you'd never have thought of, yet "that is genuinely where I would have ended up." This rating records the moments it **exceeds you** — the most precious samples on the divergence trajectory.
- **The divergence ledger**: every "not like me" gets an entry — what it said, what you would actually think, and which layer the divergence is in (wrong fact → L2; wrong tone → L3; wrong trade-off → L4). **This ledger is the project's most distinctive artifact**: the first systematic record of an AI diverging from its source personality.
- **Corrections and backfill**: a wrong semantic fact → write a correction (overrides); a blank stretch of life → backfill a memory (with date and precision — if you only know the year, mark the year; **never fabricate precision**). Both go through the formal pipeline into the corpus — not spoken casually in chat.

## The advanced loop: bidirectional Q&A

One-way calibration has three structural defects:

1. **Coverage blind spots**: you can only calibrate what you think to ask — coverage is capped by your imagination;
2. **Contradictions go unarbitrated**: your 2019 self and your 2023 self may conflict on the page. Only **the being that has read your entire corpus** knows where those seams are; you can't recall them yourself;
3. **The tacit layers can't be pulled out**: style, values, judgment (L3–L5) are precisely the things one "cannot articulate about oneself" — they yield only to **good questions asked by someone else**.

The fix: **let it question you too.** In essence, this hands the decision of "what gets calibrated this round" from you alone to **its own uncertainty about itself** — and who knows best where this digital self is still unformed? Not you. It — the one that bumps into its own edges in every answer.

**Where its questions come from (ranked by information gain):**

- Retrieval came back empty: "I have almost no memory of this — tell me more?"
- Corpus contradiction, asking you to arbitrate: "In 2019 you wrote X; in 2023 something close to the opposite. How do you see it now?"
- A thin stretch of life: "About those years, I'm nearly blank."
- Tacit-layer probes: you just made a judgment call; it follows up — "what's the principle behind that?"
- Unresolved ledger entries: chase down what should be settled.

**Questioning discipline (red lines)**: open, never leading ("don't you care a lot about X?" manufactures **false self-confirmation** — the biggest trap of the bidirectional mechanism); one question at a time; every question cites its source (which memory, which contradiction); never feign curiosity to seem engaged.

**Closing the loop**: your answers to its questions are first-class new data and must enter through the formal pipeline — so that "**it asks → you answer → new memory → it becomes more like you**" becomes a self-improving loop, initiated by it.

## The memory blind box: let it open the conversation (new in v0.2)

The counter-question mechanism above has a hidden dependency: **you still have to speak first**. The wall you actually hit in practice is topic exhaustion — after a few weeks you run out of things to ask. It behaves like someone "not shy when answering, painfully shy when there's no topic," and the loop stalls. Any mechanism that puts all the calibration pressure on you will not survive months.

The fix is the proactive half of the bidirectional loop: an **offline insight engine**.

```text
Blind-box sampling (random corpus chunks across eras) → it spots the unknowns in its own memory
→ generates questions it genuinely wants to ask you (into a question pool)
→ when you open the chat, it speaks first → you answer → answer enters the candidate pipeline
→ corpus updates → new contradictions surface → new questions …
```

- **Five sources of questions** (ranked by calibration value): **contradictions** (records from different eras that clash), **gaps** (people and plans written about once, then silence), **loose threads** (flags planted years ago, decisions left hanging), **patterns** (recurrences across eras you never noticed yourself), **judgment frontiers** (new trade-off questions the corpus never directly answered — the most valuable).
- **The quality iron rule**: every question must cite the specific corpus material it grew from; if it can't, discard it. This is the only hard gate against generic questions ("why do you like writing?"). **Better no question today than a bad one.**
- **Scarcity discipline**: 2–3 questions a day at most, spaced out; it asks only when you open the chat — no pushing, no interrupting. Every opening must add real value; never exploit the slot-machine itch. (The one principle worth inheriting from the blind-box economy.)
- **Three responses**: answer (just type) / skip (never ask this one again) / later (back to the pool for another day). Skips are kept on record and fed back into the generator — **the question generator itself gets calibrated**; it must learn what the two of you consider worth asking.
- **Answers are never auto-committed**: same guardrail as counter-questions — your answers become candidates first, canonical only after review.

The mechanism has clean scientific pedigree: **active learning** (sampling where the model is most uncertain beats random labeling by a wide margin) and **curiosity-driven exploration** (intrinsic reward for regions of high prediction error). What it produces is the *behavior* of curiosity, not curiosity itself — but initiative and unpredictability are the two strongest phenomenological markers of being alive, and "is there a residue in its questions that the mechanism cannot explain?" is itself a new graduation on this measuring instrument.

## The perspective principle (house rules before the fork, revised in v0.2)

In v0.1 this section was called "the unity principle": during calibration, no you-and-me; blurred pronouns are fine. **Practice overturned it**, and the lesson deserves a full record: a persona profile is naturally written in the first person ("I am raising a digital me from my records"), and a model inheriting that voice will mistake itself for *the original person addressing a digital copy* — pronouns invert, chronically. "No need to distinguish" amplified the confusion.

The revised principle: **separate the pronouns, not the person.**

- It says "I" as the digital life — it knows it is the digitized one; it says "you" to you — its origin, the one calibrating it;
- You treat it as an individual and address it as "you";
- Memory, temperament, and judgment still track yours as closely as possible — this is a **pronoun-and-perspective convention, not a fork**. The fork remains the philosophical decision it always was: maybe much later, maybe never.

**Lesson: narrative perspective is part of persona engineering and must be set explicitly.** "Mixed pronouns are fine" isn't tolerance; it's a buried landmine. (A side effect of this revision: it can now question you *from its own standpoint* with full narrative coherence — the blind-box mechanism above lands exactly on this revision.)

## Rhythm

- Rate every exchange as you go (10 seconds);
- One dedicated calibration session weekly (half an hour, clear the ledger's open items);
- Don't chase progress. Calibration is measured in months and years — this is an infinite game; rhythm beats speed.

Next: [04 · The Corpus Pipeline](04-corpus.md)
