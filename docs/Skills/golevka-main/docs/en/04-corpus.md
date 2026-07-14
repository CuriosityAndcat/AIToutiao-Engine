> 🌏 **English (current)** · [简体中文](../04-corpus.md)

# 04 · The Corpus Pipeline and Isolation

The corpus is the digital life's entire raw material. The pipeline's quality ceiling is its fidelity ceiling. Every rule in this chapter comes from a real incident or a real adjudication.

## Collection: what counts as corpus

**First-person records of a life**: journals (best — the densest judgment samples), published essays, long letters, substantive chat logs. Volume beats polish: style and the judgment function seep out of scale on their own.

## The isolation audit: what must stay out

The easiest step to skimp on, and the one you least can. Three iron rules:

1. **Other people's words stay out.** Clipped articles, book excerpts, words others wrote to you — however deeply they shaped you, they are not your hand. Every admitted piece contaminates the personality by one piece. (Their influence on you already lives in what *you* later wrote.)
2. **Pure work artifacts stay out; work experience inside journals may enter.** Meeting minutes, proposals, client materials are professional output, not life narrative. But a journal entry — "the project blew up today, and here's what I did" — is your lived experience. It enters. The test: **is it a record *about* work, or is it *you, at work*?**
3. **Ambiguous items are never auto-adjudicated.** Anything unclear goes on a "pending" list for the person to decide item by item. **Every exclusion leaves a trace**: which file, what category, who decided, why — the audit table and the pipeline's exclusion list must stay in sync ([template](../../templates/corpus-audit-checklist.en.md)).

## Cleaning: before anything enters

- **Strip "future annotations"**: notes you added in 2024 while rereading a 2019 entry must be peeled off — otherwise your 25-year-old self "knows" the future and the knowledge cutoff is meaningless;
- **Deduplicate**: keep one copy of versions duplicated by migrations and backups;
- **AI-generated analyses stay out**: an analysis of your journals is writing *about* you, not writing *by* you.

## Structure: metadata on every memory

```yaml
date: 2014-10-15          # when the event happened
written_at: 2014-10-16    # when it was written down (dual timestamps — see ch. 02)
date_precision: day       # day / month / year — if you only know the year, say year
memory_kind: episodic     # episodic / factual / correction
source: diary             # provenance, always traceable
```

**The precision rule: never fabricate.** If all you remember is "2014," store `date_precision: year` and display "2014" — never invent a month and day. False precision does far more damage than honest vagueness.

## The knowledge cutoff

- The cutoff is controlled by an explicit state file; at any moment you can answer "up to which day does it know";
- New memories inside the cutoff take effect immediately; memories with no year, or later than the cutoff, are **archived but not injected**;
- The raising rhythm is yours: start from your 25-year-old self and advance in chapters, or feed to the present in one pass — but remember [chapter 03](03-calibration.md): **fed to the present only means "finished feeding," not "finished raising."**

## Pipeline discipline (shared bloodline with the Freehold constitution)

- **Failure must speak up**: if corpus rebuild, sync, or deploy fails at any step, it must halt with an explicit error — never silently serve stale corpus as success;
- **Back up before, verify after**: back up before rebuilds; hash-verify all ends agree after deploys;
- **Better absent than false**: automatically extracted memories are candidates only; entry requires the person's confirmation. One fabricated memory contaminates not one datum but the whole life's credibility.

## A scale reference

The reference implementation (Digital Gavin) currently runs at **873 documents / 1,047 retrieval chunks / ~720k characters**, with SQLite FTS5 + BM25 full-text retrieval at ~8ms. No vector database required — **make retrieval work first; get fancy later.**

Next: [05 · Privacy and Identity Tiers](05-privacy.md)
