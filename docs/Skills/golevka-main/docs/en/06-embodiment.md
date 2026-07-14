> 🌏 **English (current)** · [简体中文](../06-embodiment.md)

# 06 · Vessels and Organs of Expression

The corpus and calibration answer "who it is." This chapter answers "**how it is present**." A digital life that can only wait passively in a text box — however much like you — lacks one thing: presence. Presence comes from two things: a voice, and initiative.

## The voice loop: cascade, not end-to-end

Giving it a voice comes down to one architectural decision: **use a cascaded pipeline (speech recognition → persona engine → speech synthesis), not an end-to-end realtime voice model.**

End-to-end voice models have dazzling latency, but they are sealed brains — your persona prompt can't be injected, corpus retrieval can't be inserted, the calibration loop can't be attached. And the persona engine is the whole point of this project. The cascade costs 2–4 seconds per turn, and buys you this: **the voice is just a different mouth; the brain is still the one you've calibrated across hundreds of rounds.** Fidelity beats latency, always; latency can be optimized later with streaming synthesis, but fidelity lost is everything lost.

An unexpected synergy: teaching it to **speak briefly** during calibration (like late-night messaging — say it fully, then stop) began as a text-experience fix, but lands on voice as exactly the rhythm conversation needs — monologues simply don't work out loud.

## Turn-taking rhythm: the portable tuning parameters

"Talk like a phone call" is not any piece of code. It is a set of **rhythm parameters**: what energy threshold counts as speech, how many milliseconds of silence mean you've finished, the hard cap per utterance, how soon it starts listening again after answering, whether it can be interrupted mid-sentence.

There is no correct answer to these — only answers that *feel right*, and they can only be tuned through real use. Therefore: **tune the rhythm on the cheapest vessel first (a web page); the parameter table is the asset.** When you later migrate to any body — a desk robot, a speaker, a car — copy the parameters, rewrite the shell.

## The voice is part of the persona too

Voice cloning adds a sensory dimension to "like me" — but the engineering order must be: **wire the circuit with whatever voice is most convenient first; optimize the timbre later.** If the mechanism doesn't run, a perfect voice is decoration; once it runs, swapping voices is one function change. Don't let "I want the perfect voice" block "I can talk to it today."

## Proactive output: the digital life's organs of expression

This methodology's final claim about vessels is one sentence:

> **A digital life should, based on its long-term memory and current state, actively decide when, through which medium, to bring what before you.**

Search and recommendation serve "I know what I'm looking for." A digital life's proactive output serves the other problem — **you don't know what you should be asked, or what you should encounter.** [Chapter 03's memory blind box](03-calibration.md) is the first organ of expression: it spots unknowns in your memory and speaks first when you appear. The same organ with a different output end becomes a daily digest, a printed slip of paper, or a desk robot's opening line.

## What migrates and what doesn't

Before changing bodies, know what travels:

| Travels (the real assets) | Doesn't (consumables) |
|---|---|
| The whole server-side chain: retrieval, persona engine, calibration & memory APIs | Any particular front-end's code |
| The turn-taking parameter table (the tuned feel) | Any platform's UI |
| The principles: cascade first, fidelity first, scarcity first | |

**Bodies can be replaced again and again; the organ interfaces stay.** The web page is only its first body.

Previous: [05 · Privacy & Identity Tiers](05-privacy.md) · Back to [README](../../README.en.md)
