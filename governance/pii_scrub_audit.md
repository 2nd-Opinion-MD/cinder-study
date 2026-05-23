# PII scrub audit policy

This document is the open description of the PII-scrubbing pipeline applied to every PTV before it transits the `cinder-study` analytic environment. Per protocol §9.4, the pipeline is open in its rules and audit trail; the M9 Reflex Suppression Core that the pipeline is structurally aligned with remains 2OPMD proprietary.

## Scrub stages

1. **Source-PII inventory.** Every PTV source carries a discoverable PII inventory (patient name + variants, MRN, DOB + variants, phone, address tokens, facility names, source filename, provider names, family-member mentions). The inventory is enumerated by audit before any scrubbing is performed.
2. **Replacement table.** A 27-rule replacement table is applied recursively to every string value in the PTV JSON tree. Long / specific patterns fire first; generic single-token patterns fire last (so "Norman Eric Roberts" never pre-empts a richer match).
3. **Lookaround guards.** Replacements use lookaround guards `(?<![A-Za-z])` / `(?![a-z])` rather than `\b` so that EHR-extracted text running name tokens up against digits with no whitespace (e.g. `"925-210-8834Norman"` or `"94598925"`) is still caught, while legitimate longer words like `"Robertsian"` or `"Normandy"` are preserved.
4. **Structural redaction.** The patient `metadata.patient_dob` field and any `index_by_year` keys are redacted regardless of textual content.
5. **Internal patient_id retained.** The internal `patient_id` UUID is retained as a random identifier minted by 2OPMD; it has no link-back to identity without 2OPMD's internal mapping table.
6. **Post-scrub leftover audit.** A targeted leftover-token scan re-checks the scrubbed file against the source PII inventory. If any token survives, the audit reports `RESULT: NOT CLEAN` and the scrubbed file is rejected.
7. **Provenance stamp.** The scrubber writes a `metadata.pii_scrubbed` block into the scrubbed JSON containing scrubber identity, scrub date, rules applied, and replacement counts by label. This block is what `scripts/pii_tripwire.py` checks to confirm a PTV is safe to commit.
8. **Audit transcript retained.** The replacement-count + leftover-scan transcript is committed alongside the scrubbed PTV (e.g. `fixtures/real_ehr_632event/SCRUB_AUDIT_NOARCS_20260423.txt`).

## Repository-level enforcement

Three layers prevent unscrubbed PTVs from entering the repository:

1. **`.gitignore` deny patterns.** `*_full_*.json`, `*_pretty.json`, `*_indexed_*_v1.json`, `*_indexed_*_v1_noarcs.json`, etc. are denied with `_scrubbed_pretty` allowlisted.
2. **`scripts/pii_tripwire.py`.** Pre-commit hook + CI step that scans every JSON for residual PII tokens AND blocks any PTV-shaped JSON without a verified `metadata.pii_scrubbed` block. See `tests/unit/test_pii_tripwire.py` for behavioral coverage.
3. **`scripts/validate_schemas.py`.** PTV input contract schema validation runs alongside the tripwire and rejects malformed records.

## Audit trail

| Date | Source | Scrubber commit | Audit result | Audit file |
|---|---|---|---|---|
| 2026-04-23 | `ptv_46860f06-..._indexed_20260423T202542Z_v1_noarcs_pretty.json` | 2ndOpinionMD-MVP `server/scripts/scrub_real_ptv.py` | **CLEAN** (0 leftover tokens, 27 rules, 1,114 total replacements) | `fixtures/real_ehr_632event/SCRUB_AUDIT_NOARCS_20260423.txt` |

## FORWARD data scrub policy

When the FORWARD slice arrives (target early June 2026 per Adam Cornish), the scrub pipeline will be re-run with the source-PII inventory regenerated for the FORWARD-specific schema (de-identification at source per UNMC DUA Option B, with belt-and-suspenders scrub on receipt). A new audit row will be added to this file for every batch.

The unscrubbed FORWARD slice will **never** transit `cinder-study/`. It lives only inside the 2OPMD analytic environment and is loaded into the analysis pipeline via the receiving-side ingest tooling described in `IMPLEMENTATION_PLAN.md` Phase 1.

## Modifications to this policy

Any change to the replacement table, lookaround guards, or audit procedure requires:

1. A commit to `2ndOpinionMD-MVP/server/scripts/scrub_real_ptv.py` with the new rules.
2. Re-run of the scrubber against every existing reference PTV in `fixtures/`.
3. Update of this file with a new audit-trail row for each regenerated fixture.
4. Notification to Andras + governance lead.

Reduction of the replacement table requires explicit approval; expansion does not (additional rules are always safe).
