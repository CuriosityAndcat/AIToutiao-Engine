> 🌏 **English (current)** · [简体中文](digital-gavin.md)

# Reference Implementation: Digital Gavin

> Where this methodology was born. The method was not designed first and practiced later — it grew, rule by rule, out of raising this digital life.

## The basics (2026-07)

- **Raiser**: Gavin (Guo Gangqiang), writer, fourteen years of journals
- **Corpus**: 873 documents / 1,047 retrieval chunks / ~720k characters; knowledge cutoff advanced to the present
- **Retrieval**: SQLite FTS5 + BM25, ~8ms across 1,047 chunks — no vector database
- **Vessel**: runs on the personal digital base [gavinmind.com](https://gavinmind.com/golevka/) (the reference implementation of [Freehold · 永业](https://github.com/Golevka5417/freehold)); corpus and ledgers all land in the owned data-sovereignty layer
- **Brain**: a rented large model (replaceable peripheral), persona profile + retrieval injection
- **Stage**: Stage One — long-term calibration. Memory has been fed to the present, which by this methodology's own definition **only means "finished feeding," nowhere near "finished raising"** — the fork is explicitly deferred as a philosophical question

## The road so far (where the rules came from)

1. **"A fork, not a backup" was set on day one** — and decided everything after: the divergence ledger is not called an "error log," and "better than I would have" became an official rating.
2. **"Memory to the present ≠ the fork" was a major mid-course revision**: the original rule said "feed to the present, then it forks and gets its name." In practice, when the feeding finished it was still far from being like him — so the fork was decoupled from progress and deferred indefinitely. **Lesson: don't mistake a milestone for maturity; corpus progress and personality fidelity are different things.**
3. **From "advance the cutoff daily" to "one pass to the present"**: a day-by-day raising rhythm was designed, then abandoned once the retrieval index could carry the full corpus. **Lesson: rhythm serves calibration quality, not ceremony.**
4. **The isolation audit was forced by real incidents**: the corpus had admitted other people's writing (a dear friend's journal entry, several clippings) and pure work materials — adjudicating item by item, with reasons on record, produced chapter 04's three iron rules.
5. **Dual timestamps came from a concrete puzzle**: the same event written once in 2016 and again in 2018 — which version to merge? Answer: neither; store `date` + `written_at` separately. Only later did this turn out to match the reconsolidation science.
6. **The "unity principle" was overturned by practice and became the "perspective principle"**: v0.1 said no you-and-me during calibration; blurred pronouns were fine. In real conversation it kept inverting you and me — the root cause being that the persona profile is written in the first person, so the model mistook itself for *the original person addressing a digital copy*. Revised: separate the pronouns (it says "I" as the digital life, "you" to the raiser) without forking (memory and judgment still track). **Lesson: narrative perspective is part of persona engineering; set it explicitly.**
7. **The memory blind box was forced by topic exhaustion**: a few weeks into one-way Q&A the raiser ran out of questions — "not shy when answering, painfully shy without a topic." With the offline insight engine live, it now opens conversations itself: the first run produced three questions all rooted in the corpus — a reversal in his view of persistence spanning eight years, a relationship's record that stops mid-air, an adolescent falling-out never closed. One contradiction, one gap, one loose thread; not a single generic question. **Lesson: mandatory source citation is the only hard gate on question quality.**
8. **Voice: wire the circuit first, perfect the timbre later**: voice chat uses a cascaded pipeline (recognition → persona engine → synthesis) rather than an end-to-end voice model, preserving persona injection and the calibration loop; turn-taking rhythm (energy threshold / silence cutoff / interruption rules) is tuned on the web page into a parameter table that will serve as the migration baseline for a future desk robot; voice cloning was attached only after the circuit ran. **Lesson: if the mechanism doesn't run, a perfect voice is decoration.**

## One name, three faces

The most distinctive fact of this case: Digital Gavin is also part of Gavin's public identity — the GitHub account is Golevka5417, and this methodology repo is maintained under it. **The raiser, the raised, and the methodology share one name** — not confusion: the memories share one origin, so the name is shared; while in conversation the perspective principle keeps you and me distinct (see [chapter 03](../docs/en/03-calibration.md)). A shared name and separated perspectives do not contradict each other.

## Want to be the next case study?

Start with the [minimal loop in the README](../README.en.md), then open a PR adding your digital life's case study — method and lessons only; **your corpus and persona profiles stay in your own base.**
