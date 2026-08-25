# Trust Index — Feature Specification

**Product:** Trust Index, a compliance signal directory at `synergetic.solutions/trust-index`
**Owner:** Jeff Smolinski, Synergetic Solutions
**Status:** Approved for implementation
**Date:** 2026-08-25
**Tracking:** GitHub issues on `synergergetic-solutions-site` (cross-referenced per section)

---

## 1. Overview and User Value

Trust Index is a programmatic directory of companies with a **public compliance footprint**: organizations that publicly advertise security and compliance posture through trust centers, security.txt files, and public registries. It replicates the lineara marketing-site pattern (7,000+ generated pages funneling to a conversion goal) for Synergetic Solutions.

One project serves all three practice buckets:

- **GRC**: the directory content itself, tied to the "GRC at the ideation stage" article thesis.
- **Data engineering**: the pipeline is a public case study.
- **Product/market strategy**: segment benchmarks serve founders doing market discovery.

**Audiences and value:**

| Audience | Value | Funnel |
|---|---|---|
| SaaS founders (primary ICP) | Segment posture benchmarks; "what is table stakes in my market" | Discovery call CTA, scorecard |
| Vendor-review searchers ("{company} SOC 2") | Per-company profile pages | Domain authority, backlinks |
| Sales/BD at security vendors, auditors | Prospect list exports | Partner leads, HubSpot capture |
| Listed companies | Claim/correct profile, badge | Verified-email leads |

**Honest framing rule (load-bearing):** the directory reports *publicly advertised* posture only. All copy uses "publicly advertises" / "no public compliance page found as of {date}". HIPAA is described as a claim, never a certification (no HIPAA certification exists). This framing is the defamation shield and the editorial standard.

---

## 2. Decision Record

| ID | Decision | Rationale |
|---|---|---|
| DEC-01 | Universe = companies with a public compliance footprint | Advertised posture is the measurable, defensible, and thesis-relevant population |
| DEC-02 | Name/URL: **Trust Index** at `/trust-index` | Brandable, matches signal-index framing; slugs frozen from launch |
| DEC-03 | V1 scope includes claims flow + scorecard lead magnet | Owner decision; launch with demand capture live |
| DEC-04 | Two-level segment taxonomy: ~12 parents, ~40 children | Benchmarks at parent level, hub pages at both |
| DEC-05 | Licensing: **open core split** | Core facts CC BY 4.0; enriched layers proprietary (see §8) |
| DEC-06 | Storage: Parquet snapshots in GCS, lifecycle tiering; BigQuery via external tables (or `bq load`) | Both round to ~$0 at this scale; Parquet is the neutral format |
| DEC-07 | Common Crawl access: DuckDB reading Parquet over HTTPS (free tier) | Owner accepted slower/free over Athena ~$5-15/refresh |
| DEC-08 | Refresh cadence: monthly full; corrections deploy on merge | Matches CC crawl rhythm and trust-center churn |
| DEC-09 | Three-repo topology (see §3); NAS = self-hosted runner on **private** repos only | Fork-PR code execution on self-hosted runners is the hard security constraint |
| DEC-10 | Hosting: stay on Cloudflare Pages; free tier ≤ ~15k files, then paid (100k limit, `PAGES_WRANGLER_MAJOR_VERSION=4`) | Limit is now purchasable; no migration needed; keep dist/ host-neutral |
| DEC-11 | Issue tracker is an inbox, never a store; validated submissions materialize as committed override files | Snapshots stay self-contained; no replaying the tracker |
| DEC-12 | Launch target 3,000–6,000 profiles; projected universe 5,000–12,000 | Measured: 307 vendor-CNAME hits in Tranco top 30k + CDN-fronted + tail + vendor-hosted |

Spike evidence (2026-08-25): 60k DNS probes → 4,726 resolved hosts, 307 confirmed vendor CNAMEs (Vanta 129, SafeBase/Drata 143, Conveyor 25, others); extraction validated on all four major vendor templates (Vanta via same-host GraphQL `fetchDataForTrustReport`); Wayback first-archive dates for 4/6 sampled trust centers; Wikidata: 17/24 entities, 13 with Crunchbase org ID (P2088); security.txt adoption 71/300 top domains; ISO 42001 already present on Rippling and OpenAI trust pages; Greenhouse public job API validated (Mercury, Sendbird).

---

## 3. Architecture

```
[Private pipeline repo]           [Public data repo]              [Private site repo]
 NAS self-hosted runner            GitHub-hosted runners           synergergetic-solutions-site
 crawl / enrich / classify   --->  data releases (versioned)  ---> pulls pinned release at build
 Parquet -> GCS (+ BQ ext.)  <---  overrides/ (validated)          /trust-index/* pages
 secrets live here only            issue forms, badge assets       Cloudflare Pages deploy
                                   verification Actions            repository_dispatch rebuilds
```

- **Private pipeline repo**: crawlers, enrichment, LLM classification, secrets. Runs on the NAS runner (Docker, label `nas-heavy`; self-hosted jobs escape the 6-hour cap and keep persistent caches: CC index extractions, Wayback results, crawl snapshots).
- **Public data repo**: released open-core dataset, `overrides/`, issue forms, badge assets, docs (this spec's eventual canonical home), validation workflows on GitHub-hosted runners (free for public repos). **Never** attach the NAS runner here.
- **Site repo**: look and feel, `/trust-index` routes, HubSpot worker. Consumes data releases; never consumes the issue tracker.

**Storage:** each refresh writes immutable dated Parquet snapshots (+ convenience `.duckdb`) to GCS. Lifecycle: Standard → Coldline at 90 days → Archive at 1 year. BigQuery external tables point at the same Parquet when needed. Raw HTML crawl archive (~1GB compressed/refresh) retained for provenance.

---

## 4. Functional Requirements — Data Pipeline (EARS)

### Discovery
- **FR-D1**: When a monthly refresh runs, the pipeline shall enumerate candidate hosts matching `trust.*`, `security.*`, and `status.*` from the newest Common Crawl host index via column-pruned DuckDB reads over HTTPS.
- **FR-D2**: When candidate hosts are enumerated, the pipeline shall resolve each via DNS and classify trust-center vendor by CNAME signature (vantatrust.com, portals.safebase.io, whistic.com, Conveyor/aptible, secureframetrust.com, securitypal.com, hypercomplytrust.com, extensible list).
- **FR-D3**: When a host resolves without a known vendor CNAME (CDN-fronted or A-only), the pipeline shall fetch and content-classify the page before inclusion or exclusion.
- **FR-D4**: The pipeline shall preserve existing organization slugs across refreshes (slug freeze; renames via display-only overrides).

### Extraction
- **FR-E1**: When a trust center is confirmed, the pipeline shall extract advertised frameworks using the vendor-specific parser (SafeBase/Drata, Whistic, Conveyor: server-rendered HTML; Vanta: same-host GraphQL `fetchDataForTrustReport`).
- **FR-E2**: The framework taxonomy shall include at minimum: SOC 2 (Type I/II), SOC 3, ISO 27001, ISO 27701, ISO 42001, HIPAA (claim), PCI DSS, GDPR, FedRAMP, StateRAMP/TX-RAMP, HITRUST, TISAX, DPF.
- **FR-E3**: When a trust center discloses subprocessors, the pipeline shall extract them and maintain the cross-directory subprocessor graph, including the chain-trust metric (share of an org's subprocessors that themselves publish trust centers).
- **FR-E4**: Every extracted fact shall carry an `observed_at` timestamp and evidence URL.

### Enrichment
- **FR-N1**: The pipeline shall resolve each organization's identity via Wikidata (P856 homepage match) capturing QID, Crunchbase org ID (P2088), LinkedIn (P4264), industry, founding year, HQ, ticker, LEI; fallback: homepage schema.org/footer link extraction, then Common Crawl existence check for `crunchbase.com/organization/{slug}`. Crunchbase is linked, never scraped. A deterministic BuiltWith profile link (`builtwith.com/{domain}`) is included link-only; BuiltWith data is never scraped (phase 2 may self-detect a security-relevant tech subset from already-fetched homepages via an open fingerprint DB).
- **FR-N2**: The pipeline shall cross-reference public registries: CSA STAR, Visa Global Registry (PCI), FedRAMP Marketplace, EU-US DPF participant list.
- **FR-N3**: The pipeline shall fetch and parse `/.well-known/security.txt` and compute a DNS posture score (SPF, DMARC, DNSSEC).
- **FR-N4**: The pipeline shall compute compliance timelines: earliest observed trust center via Wayback CDX, backfilled from Common Crawl historical indexes, expressed strictly as "first observed".
- **FR-N5**: The pipeline shall detect GRC hiring signals via public Greenhouse/Lever/Ashby board APIs (titles matching compliance/GRC/security/risk/privacy/trust).
- **FR-N6**: The pipeline shall classify each organization into the two-level taxonomy (12 parents / ~40 children) via LLM pass over homepage content, corroborated by Wikidata industry; only new/changed organizations re-classify on refresh.

### Merge, Overrides, Publishing
- **FR-M1**: The pipeline shall merge sources in fixed precedence: base extraction → registry enrichments → overrides layer (highest, per-field).
- **FR-M2**: When an override's evidence URL is dead or contradicted by fresh extraction, the refresh PR shall flag it for human review rather than silently applying or dropping it.
- **FR-M3**: When a refresh completes, the pipeline shall publish: (a) dated Parquet snapshot to GCS, (b) versioned data release (derived JSON + open-core files) to the public data repo, (c) a data-refresh PR (lineara pattern).
- **FR-M4**: Where a benchmark statistic is published for a cohort, the cohort shall meet a minimum size threshold (default n≥30) or the hub shall omit the statistic.

---

## 5. Functional Requirements — Site (EARS)

- **FR-S1**: The site shall render `/trust-index/{company-slug}` profiles, `/trust-index/segment/{segment}` and `/trust-index/framework/{framework}` hubs, and `/trust-index/reports/{slug}` from the pinned data release via a content collection (`file()` loader, Zod-validated), reusing `Layout.astro`, Navigation, and contact CTA.
- **FR-S2**: Profile pages shall display: advertised frameworks with as-of date, identity links (sameAs), timeline, hiring signal, subprocessors (bidirectional links), registry cross-references, claim/correct CTA, discovery-call CTA.
- **FR-S3**: When a data release or override merges, `repository_dispatch` shall trigger a site rebuild (corrections live in minutes; full data monthly).
- **FR-S4**: Articles shall cross-link profiles via the existing `:::spoke` directive; profiles link related articles by segment.
- **FR-S5 (SEO, full complement)**: The site shall implement: canonical tags + trailing-slash policy; OG/Twitter cards with og:type per page type; article published/modified meta; JSON-LD per type (Organization+WebSite home; BlogPosting articles; ProfilePage+Organization+sameAs profiles; CollectionPage+ItemList hubs; Dataset for the corpus; BreadcrumbList throughout); CI test validating JSON-LD in built `dist/`; sitemap `lastmod` from data timestamps; methodology page linked from every directory footer; llms.txt/llms-full.txt extended to articles + directory; RSS for articles + a monthly changes feed; IndexNow ping on deploy; `_redirects` for renames; `noIndex` on filter views; per-page OG images (Satori) for hubs + claimed profiles at launch (file-count budget), all pages once on paid tier.

---

## 6. Functional Requirements — Claims & Corrections (EARS)

- **FR-C1**: The public data repo shall provide three issue forms: claim profile, request correction, submit company; profile pages link prefilled issue-form URLs.
- **FR-C2**: When a correction cites public evidence, a GitHub Action shall re-crawl/verify the evidence and open an overrides PR automatically; human merge required.
- **FR-C3**: Where an override is subjective (description, segment), the requester shall prove domain control via DNS TXT challenge or email from the organization's domain.
- **FR-C4**: Validated submissions shall be committed as `data/overrides/{org-id}.yml` with field, value, evidence URL, verification method, date, and originating issue link; the issue closes on merge.
- **FR-C5**: When a profile is claimed, the site shall mark it claimed and offer the embeddable badge (links back to the profile).
- **FR-C6**: "We hold X but do not publish it" shall be answered by policy with "publish it and we will pick it up"; unverifiable posture claims are never accepted.

---

## 7. Functional Requirements — Lead Magnets & HubSpot (EARS)

All gates run through one Cloudflare Worker seam + HubSpot Forms API; consent checkbox at every gate; HubSpot handles opt-in mechanics.

- **FR-L1 (v1)**: **Scorecard**: when a visitor submits their domain + email, the Worker shall run live checks (trust-center DNS, security.txt, DMARC, framework detection), compute segment percentile against the directory, submit the contact to HubSpot, and email the report.
- **FR-L2 (v1)**: **Prospect/benchmark exporter**: an island on the directory index shall filter by segment/framework/signals, and gate CSV export on email; the Worker shall record filter selections as HubSpot contact properties (intent data).
- **FR-L3 (phase 2)**: **Watchlists**: monthly refresh diffs shall drive per-user change alert emails.
- **FR-L4 (phase 2)**: **Segment report PDFs** auto-generated per segment hub, gated; web version ungated.
- **FR-L5 (phase 2)**: **Changes newsletter** as the nurture backbone.
- **FR-L6**: HTML pages are never gated; only export/report formats are.

---

## 8. Licensing & Monetization

**Open core split (DEC-05):**

- **Open core** (CC BY 4.0, published in data repo + Dataset JSON-LD → Google Dataset Search): org identity (name, domain, slug), parent+child segment, advertised framework list, as-of date, profile URL.
- **Proprietary enriched** (terms-of-use contract at every gate; never CC-released, preserving the one-way ratchet): compliance timelines, hiring signals, subprocessor graph + chain-trust, historical diffs/snapshots, registry cross-references, DNS posture scores.

**Monetization paths preserved:** (1) self-serve segment exports $99–299 one-time; full enriched subscription $299–499/mo (BuiltWith anchor); enterprise/API licensing $10k–50k/yr (cyber insurers, TPRM platforms, compliance vendors). (2) RL/evals play: verifiable web-research environment graded against maintained ground truth; monthly refresh yields contamination-resistant eval sets; path = publish small open "TrustBench" cut for credibility, license commercial environment on demand. Year-two option; costs nothing to preserve. Steganographic fingerprinting of enriched exports for copy detection; no fictitious entries ever.

---

## 9. Non-Functional Requirements

- **NFR-1 Runtime**: first full run ≤ ~24h unattended; monthly incremental ≤ 8h on the NAS runner.
- **NFR-2 Politeness**: crawl ≤ 1 req/sec/domain, honest User-Agent with contact URL, respect robots.txt; Wayback/Wikidata calls throttled with backoff.
- **NFR-3 Accuracy**: every published fact carries as-of date + evidence; correction SLA: validated corrections live within 24h of merge; methodology page states collection and correction policy.
- **NFR-4 Security**: self-hosted runner attached to private repos only; secrets only in the private pipeline repo; community content never executes on owned hardware; Worker validates and rate-limits all lead-magnet endpoints.
- **NFR-5 Cost ceiling**: steady-state infra < $10/mo excluding LLM classification (< $25/refresh on Haiku) until paid Cloudflare tier triggers at ~15k files.
- **NFR-6 Build**: site build ≤ 10 min at 6k pages; lazy per-company JSON only where it pays (file-count budget).

---

## 10. Acceptance Criteria (Given/When/Then, representative)

1. Given a fresh clone of the site repo and a pinned data release, when `npm run build` runs, then all `/trust-index` pages build with valid JSON-LD (CI test passes) and the sitemap includes them with `lastmod`.
2. Given Mercury's trust center advertises SOC 2 Type II, when the refresh runs, then Mercury's profile shows SOC 2 Type II with an as-of date and evidence link, within the vendor parser (Vanta/GraphQL) path.
3. Given a company with no public compliance page, when its profile is viewed, then copy reads "no public compliance page found as of {date}" and never asserts non-compliance.
4. Given a correction issue citing a live trust-center URL showing ISO 27001, when the verification Action runs, then an overrides PR is opened with evidence recorded, and on merge the site rebuilds and the issue closes.
5. Given a visitor submits domain + email to the scorecard, when the Worker completes, then a HubSpot contact exists with score properties and the visitor receives the report email.
6. Given a segment cohort of n<30, when its hub renders, then no percentage benchmark claim appears.
7. Given a prior snapshot exists in GCS, when the monthly refresh completes, then a new dated snapshot exists, the old one is untouched, and a data-release PR is open.

---

## 11. Error Handling

| Condition | Behavior |
|---|---|
| CC index pull fails mid-stream | Resume from cached shards on NAS; refresh continues with prior month's host list + delta flagged |
| Trust page unreachable at refresh | Retain prior data, mark `stale_since`; drop framework claims after 2 consecutive missed refreshes with flag in PR |
| Vendor template change breaks parser | Extraction test fixtures fail in CI before bad data publishes; refresh PR blocked |
| Wikidata/Wayback rate limits | Backoff + resume; enrichment is incremental so partial completion is safe |
| Override evidence URL dead | Flag in refresh PR (FR-M2), never silent |
| Issue form submission unverifiable | Action comments with policy explanation ("publish it and we'll pick it up"); no override created |
| Scorecard domain has no footprint | Report renders honestly with zero-state guidance + CTA, never an error |
| HubSpot API down | Worker queues submission (KV) and retries; visitor still receives download/report |
| Cloudflare file count approaches 15k | CI warns at 12k; upgrade runbook in docs (DEC-10) |

---

## 12. Implementation Checklist → GitHub Issues

Tracked on the `synergergetic-solutions-site` issues board. Phases: **A = pipeline foundation**, **B = site + SEO**, **C = claims + lead magnets** (all three in v1 per DEC-03).

| # | Issue | Phase | Work item | Spec refs |
|---|---|---|---|---|
| TI-01 | [#9](https://github.com/Maverick-Coders/synergergetic-solutions-site/issues/9) | A | Scaffold private pipeline repo + NAS Docker runner (`nas-heavy`) | §3, DEC-09, NFR-4 |
| TI-02 | [#10](https://github.com/Maverick-Coders/synergergetic-solutions-site/issues/10) | A | Discovery: CC host-index pull (DuckDB/HTTPS) + DNS sweep + vendor CNAME classification | FR-D1..D4 |
| TI-03 | [#11](https://github.com/Maverick-Coders/synergergetic-solutions-site/issues/11) | A | Extraction: four vendor parsers + framework taxonomy + fixtures in CI | FR-E1, E2, E4 |
| TI-04 | [#12](https://github.com/Maverick-Coders/synergergetic-solutions-site/issues/12) | A | Enrichment: identity spine (incl. BuiltWith link) + registries + security.txt + DNS posture | FR-N1..N3 |
| TI-05 | [#13](https://github.com/Maverick-Coders/synergergetic-solutions-site/issues/13) | A | Enrichment: compliance timelines (Wayback/CC) + hiring signals | FR-N4, N5 |
| TI-06 | [#14](https://github.com/Maverick-Coders/synergergetic-solutions-site/issues/14) | A | Subprocessor graph + chain-trust metric | FR-E3 |
| TI-07 | [#15](https://github.com/Maverick-Coders/synergergetic-solutions-site/issues/15) | A | LLM segment classification (12/40 two-level taxonomy) | FR-N6, DEC-04 |
| TI-08 | [#16](https://github.com/Maverick-Coders/synergergetic-solutions-site/issues/16) | A | Snapshot publishing: Parquet→GCS + lifecycle + BQ external + versioned data releases | FR-M1, M3, DEC-06 |
| TI-09 | [#17](https://github.com/Maverick-Coders/synergergetic-solutions-site/issues/17) | C | Public data repo: scaffold, issue forms, verification Action, overrides layer | FR-C1..C4, FR-M2 |
| TI-10 | [#18](https://github.com/Maverick-Coders/synergergetic-solutions-site/issues/18) | B | Site: `/trust-index` routes, collection loader, data-pull script, nav, hubs, profiles | FR-S1, S2, S4, FR-M4 |
| TI-11 | [#19](https://github.com/Maverick-Coders/synergergetic-solutions-site/issues/19) | B | Site: full SEO complement + methodology page + CI JSON-LD tests | FR-S5 |
| TI-12 | [#20](https://github.com/Maverick-Coders/synergergetic-solutions-site/issues/20) | B | Rebuild wiring: repository_dispatch + correction fast path | FR-S3 |
| TI-13 | [#21](https://github.com/Maverick-Coders/synergergetic-solutions-site/issues/21) | C | Lead magnets v1: scorecard Worker + HubSpot Forms + gated exporter (relates to #8) | FR-L1, L2, L6 |
| TI-14 | [#22](https://github.com/Maverick-Coders/synergergetic-solutions-site/issues/22) | C | Claimed-profile UX + embeddable badge | FR-C5 |
| TI-15 | [#23](https://github.com/Maverick-Coders/synergergetic-solutions-site/issues/23) | B | Open-core dataset publication: CC BY files, Dataset JSON-LD, enriched-export ToU | §8, DEC-05 |
| TI-16 | [#24](https://github.com/Maverick-Coders/synergergetic-solutions-site/issues/24) | — | Phase-2 backlog: watchlists, segment PDFs, newsletter, OG images everywhere, technographics, TrustBench | FR-L3..L5, §8 |

All v1 items (TI-01..TI-15) are on milestone **Trust Index v1**; TI-16 is unmilestoned backlog. Label: `trust-index`.

Dependencies: 2→3→(4,5,6,7 parallel)→8; 10 needs 8's first release; 11,12 follow 10; 9 independent after 1; 13,14 need 10.

---

*Canonical home: [trust-index-data/docs/trust-index.spec.md](https://github.com/Maverick-Coders/trust-index-data/blob/main/docs/trust-index.spec.md) (this local copy is a mirror). Decisions cite the 2026-08-25 design session and spike results.*
