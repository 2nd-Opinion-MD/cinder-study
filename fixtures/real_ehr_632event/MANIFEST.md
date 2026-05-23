# Real-EHR 632-event PTV fixture — provenance manifest

This directory holds the 2026-04-23 real-EHR Patient Trajectory Vector (PTV) reference fixture used as the regression baseline for the vendored Bayesian kernel layer (per `IMPLEMENTATION_PLAN.md` Phase 4.H) and as the substrate for Andras's F4-CASE-01 / F4-CASE-04 case instantiations.

## File

| Field | Value |
|---|---|
| Filename | `ptv_real_ehr_632event_v1_noarcs_scrubbed.json` |
| Size | 3,464,232 bytes (≈ 3.46 MB) |
| SHA-256 | `F159AF9F39D05B6B811FBEDE4072E3CA66E8CD440E26782BA9CA8B19CDD1094D` |
| Event count | **632** |
| Schema variant | `ptv.2.1-indexed-v1-noarcs` (encoded in source filename) |
| Source patient | UUID `46860f06-e0a5-42d4-af9f-4dd8caa666f0` (random identifier minted by 2OPMD; no link-back to identity without internal mapping) |
| Original indexing timestamp | 2026-04-23T20:25:42Z |
| PII scrub date | 2026-04-23 |

## Chain of custody

1. **Original source** — real-EHR PDF ingest produced `ptv_46860f06-...-full_20260422T143255Z.json` on 2026-04-22 in the `2ndOpinionMD-MVP` analytic environment.
2. **Indexing pass** — re-indexed to noarcs variant on 2026-04-23T20:25:42Z, producing `ptv_46860f06-..._indexed_20260423T202542Z_v1_noarcs.json`.
3. **PII scrub** — run via `2ndOpinionMD-MVP/server/scripts/scrub_real_ptv.py` on 2026-04-23, applying 27 replacement rules. Output: `ptv_46860f06-..._indexed_20260423T202542Z_v1_noarcs_scrubbed_pretty.json`.
4. **Audit** — post-scrub leftover-token scan executed; result: **CLEAN** (zero residual PII tokens). Audit transcript at `SCRUB_AUDIT_NOARCS_20260423.txt` in this directory.
5. **Copy into `cinder-study`** — 2026-05-23 by Dylan, renamed to `ptv_real_ehr_632event_v1_noarcs_scrubbed.json` for clarity. SHA-256 verified identical to source.

## PII replacement summary (from audit)

The 27 rules applied scrubbed the following PII categories (by count of replacements):

- Address (street + city/state/zip): 235 redactions
- Phone: 117 redactions
- Patient name (full / first / last / honorific / family-member): 130 redactions
- MRN: 85 redactions
- DOB: 84 redactions
- Provider names: 18 redactions
- Facility names (Kaiser + bare + named): 17 redactions
- City (bare + trailing): 35 redactions
- Source filename: 1 redaction
- Structural (DOB year + index-by-year): 2 redactions

Post-scrub leftover scan: **0 hits** across 19 distinct PII pattern probes. See `SCRUB_AUDIT_NOARCS_20260423.txt` for the complete audit.

## Internal `metadata.pii_scrubbed` block

The fixture's own `metadata.pii_scrubbed` provenance block (read by `scripts/pii_tripwire.py`):

```json
{
    "scrubber": "server/scripts/scrub_real_ptv.py",
    "scrubbed_at": "2026-04-23",
    "rules_applied": 27,
    "replacement_counts_by_label": { ... }
}
```

Note: the internal `patient_id` UUID is intentionally retained per the scrub script's design — it is a random identifier with no link-back to identity without 2OPMD's internal mapping table.

## Use in CINDER

Per `IMPLEMENTATION_PLAN.md`:

- **Phase 4.H regression baseline.** `bayesian_update_uc` on this PTV must produce identical `point_estimate`, `band_90`, `spec_hash`, and `evidence_event_ids` to the 2ndOpinionMD-MVP run at commit `00eaa9eb`. Test ID: `regression_mvp_baseline_632event`.
- **Phase 4.B `c01_flare_detection_cinder_spec`.** Same fixture, but using the CINDER-tuned `cinder_likelihood_spec.yaml` (Pain VAS Δ ≥ 20, RAPID3 added). Asserts `point_estimate` differs from MVP default.
- **F4-CASE-01 / F4-CASE-04.** Andras's case instantiations referenced in the 2026-05-23 prep email — to be defined post-call.

## Scope

This file is **safe for inclusion in the public `cinder-study` repository** per protocol §9.1 / §9.4. It is **not** a substitute for the FORWARD data slice (early-June arrival target via DUA Option B) — this is a reference fixture for pipeline development and regression testing only, not a study cohort member.

## What is NOT in this directory

By policy, the unscrubbed source files and intermediate stages **must never** transit into `cinder-study`:

- `ptv_46860f06-..._full_20260422T143255Z.json` (compact unscrubbed)
- `ptv_46860f06-..._full_20260422T143255Z_pretty.json` (pretty unscrubbed)
- `ptv_46860f06-..._indexed_20260423T202542Z_v1.json` (compact indexed, with-arcs)
- `ptv_46860f06-..._indexed_20260423T202542Z_v1_pretty.json` (pretty indexed, with-arcs)
- `ptv_46860f06-..._indexed_20260423T202542Z_v1_noarcs.json` (compact indexed, noarcs, **unscrubbed**)
- `ptv_46860f06-..._indexed_20260423T202542Z_v1_noarcs_pretty.json` (pretty indexed, noarcs, unscrubbed)
- `ptv_46860f06-..._pg_export_*.json` (Postgres exports, unscrubbed)

These files are blocked at the repository level by `.gitignore` patterns and at commit time by `scripts/pii_tripwire.py`.

If a regeneration is needed, run from inside the `2ndOpinionMD-MVP` analytic environment:

```bash
python server/scripts/scrub_real_ptv.py \
  --input  artifacts/ptv_46860f06-..._indexed_..._v1_noarcs_pretty.json \
  --output artifacts/ptv_46860f06-..._indexed_..._v1_noarcs_scrubbed_pretty.json \
  --audit  artifacts/SCRUB_AUDIT_NOARCS_<YYYYMMDD>.txt
```

…then copy the scrubbed output (only) into this directory.
