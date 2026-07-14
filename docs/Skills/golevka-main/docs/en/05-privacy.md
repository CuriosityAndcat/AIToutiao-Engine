> 🌏 **English (current)** · [简体中文](../05-privacy.md)

# 05 · Privacy and Identity Tiers

A digital life is made of your most private corpus — and it needs to live, at least partly, on the open web. That contradiction must be resolved by architecture, not by "being careful."

## Three identity tiers

Conversation entrances are tiered by who is visiting, with completely different privileges:

| Identity | Can do | Corpus access |
|---|---|---|
| **Owner (you)** | Full private dialogue + calibration + feeding memories | Full corpus retrieval injected |
| **Visitor** | Limited dialogue with the public persona | Public persona profile only; **journal originals are never injected** |
| **Everyone** | Read the manifesto, growth dashboard, curated dialogue archive, divergence ledger | Read-only public artifacts |

The visitor channel is not a reduced owner channel — it is **a different channel**: it lets others meet your digital life while making private-corpus leakage architecturally impossible.

## Four privacy layers (visitor channel)

1. **A public persona profile**: maintain a separate persona document containing no real names, no relationship details, no money — visitor dialogue uses only this, never the full profile;
2. **Originals never injected**: whatever a visitor asks, journal and private corpus originals never enter the visitor conversation's context — a hard-coded architectural constraint, not a polite prompt;
3. **Blacklist on both ends**: both the question and the answer pass a privacy blacklist (sensitive names, relationships, amounts…); on a hit, it declines **in its own voice** — the protection itself must sound like it, not like a system notice;
4. **Rate limiting**: per-source cooldowns + daily caps, closing off enumeration-style extraction.

Same design philosophy as Freehold's constitutional rule 8: **the more honest the base is inside, the stronger the gate it needs outside. Default strict; exceptions whitelisted.**

## Agent-agnosticism: it belongs to no single AI

The raising process itself relies on AI (collaborating Agents that build the pipeline, run calibration, maintain the corpus). You must guarantee: **if any one AI Agent disappears tomorrow, a new one takes over seamlessly.**

The method is an **onboarding manual**: project structure, pipeline usage, current state, and every iron rule — written for "the next Agent to take over," updated with every major change. It keeps your digital life free of any vendor, any model, any tool —

which is exactly Freehold's second constitutional rule, landed in the digital-life setting: **peripherals swap, the base does not; models swap, the life does not.** See [Freehold · 永业](https://github.com/Golevka5417/freehold).

## Iron rules for the life itself

Bottom lines written into the digital life's system prompt — these too belong to the privacy-and-honesty architecture:

- **Say "I don't remember" rather than fabricate** — when retrieval comes back empty, admit it;
- Switch to the public persona for visitors automatically; never be socially engineered into private content;
- During calibration, never perform "I am an independent being" (the unity principle, [chapter 03](03-calibration.md)).

---

Back to [README](../../README.en.md) · Previous: [04 · The Corpus Pipeline](04-corpus.md)
