# Trust Index Data

Open-core dataset and community corrections for [Trust Index](https://synergetic.solutions/trust-index), a directory of companies with a public compliance footprint: organizations that publicly advertise security and compliance posture through trust centers, security.txt files, and public registries.

**Spec:** [docs/trust-index.spec.md](docs/trust-index.spec.md). Implementation tracking: [TI-01..TI-16](https://github.com/Maverick-Coders/synergergetic-solutions-site/issues?q=label%3Atrust-index).

## What this repo holds

- `data/open/` — the **open-core dataset** (org identity, market segment, publicly advertised frameworks, as-of date, profile URL), released under **CC BY 4.0** (see `LICENSE-DATA`).
- `overrides/` — validated community corrections and profile claims, one YAML file per organization, each carrying the evidence URL, verification method, date, and originating issue.
- `docs/` — the project specification and methodology.
- Issue forms for **claiming a profile**, **requesting a correction**, and **submitting a company** (arriving with TI-09).

## How data gets here

Everything published is **publicly observable**: what companies themselves advertise. Corrections must cite public evidence; an automated check verifies the evidence before a change is proposed, and a human merges it. Unverifiable posture claims are never accepted; the answer to "we hold X but don't publish it" is "publish it and the next refresh will pick it up."

The enriched layers (compliance timelines, hiring signals, the subprocessor graph, historical diffs) are **not** in this repo; they are proprietary and available through [synergetic.solutions/trust-index](https://synergetic.solutions/trust-index).

## Licensing

- Files under `data/open/`: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — free to use commercially with attribution to Synergetic Solutions and a link to the Trust Index.
- Everything else in this repo (docs, schemas, workflow code): all rights reserved unless marked otherwise.
