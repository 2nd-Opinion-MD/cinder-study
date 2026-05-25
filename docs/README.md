# CINDER docs

This directory holds the §13 confirmation memos, mapping documents, and confirmation logs that gate `protocol-v3.0-FINAL` tag readiness.

## §13 confirmation memos (per `PROTOCOL_DRAFT_v3 §13`)

| Memo | Status | Phase | Gate |
|---|---|---|---|
| `CONFIRM_REPO_SCAFFOLD.md` | partially closed | Phase 0 | §13.5 |
| `confirmation_software.md` | **confirmed (2026-05-24)** | Phase 1 | §13.4 |
| `confirmation_matching_rule.md` | **confirmed-with-caveats (2026-05-24)** | Phase 1 | §13.2 |
| `confirmation_omeract.md` | **confirmed-with-caveats (2026-05-24)** | Phase 1 | §13.3 |
| `CONFIRM_SAMPLE_SIZE.md` | pending | Phase 2 | §13.1 |
| `CONFIRM_MOLLARD_MAPPING.md` | pending | Phase 5 | §13.6 |

Each memo follows the same template (see `_TEMPLATE.md` once Phase 0 completes):

1. **Question** — verbatim from §13.
2. **Answer** — confirmed value(s) and rationale.
3. **Evidence** — links to the analysis output, simulation log, or external citation supporting the answer.
4. **Approval** — Andras + Dylan sign-off date and commit hash.

## Other docs

| File | Purpose |
|---|---|
| `terminology_map.md` | F2/F4 (internal 2OPMD phase names) ↔ IMPLEMENTATION_PLAN.md phases (see `IMPLEMENTATION_PLAN.md` `terminology_map` for the canonical version) |
| `architecture_overview.md` | Open-vs-closed module diagram per protocol §10 |
| `replicability_pathway.md` | Detailed description of the blinded external re-run pathway |
| `synthetic_exemplar_regeneration_plan.md` | §F2 plan for regenerating with-arcs exemplars to noarcs (addresses Andras pre-call ask #3) |
| `tuesday_call_talking_points.md` | **Internal cheat sheet for the 2026-05-26 1pm CDT call with Kaleb, Adam Cornish, and Rebecca Schumacher.** Audience: Dylan + Andras only. Not for distribution to call participants. |

These docs are populated as their gating phase completes.
