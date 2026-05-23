# Data request — FORWARD/UNMC

This directory holds the artifacts of the data-request conversation with FORWARD/UNMC: requested fields, format specs, delivery mechanism, DUA pathway, and ingest acceptance criteria. Final spec is delivered to Adam Cornish (UNMC IT) at the 2026-05-26 working call and refined as needed.

## Contents (target)

| File | Status | Owner | Purpose |
|---|---|---|---|
| `forward_field_spec.md` | drafted in `PRE_CALL_CHECKLIST.md` | Dylan | Requested field list with rationale per protocol §4 |
| `forward_format_spec.md` | drafted in `PRE_CALL_CHECKLIST.md` | Dylan | Wire format (CSV preferred), encoding, dating, separators, missingness encoding |
| `forward_delivery_spec.md` | pending Adam input | Adam Cornish + Dylan | SFTP / S3 / on-prem transfer mechanism, encryption, schedule |
| `dua_status.md` | pending UNMC IRB | Andras + Kaleb + Adam | DUA Option B (anonymized at source) status |
| `ingest_acceptance.md` | pending | Dylan | Receiving-side acceptance criteria: row count gate, schema gate, code-prevalence gate, value-distribution gate, scrub-on-receipt gate |

The `PRE_CALL_CHECKLIST.md` at the repo root is the master version of the §5 (call-targeted) and §6 (concerns) content; this directory is where post-call commitments will be formalized into stable specs.

## Pre-call status (2026-05-23)

Per `PRE_CALL_CHECKLIST.md` §5:

- **Required fields.** PRO instruments (HAQ-II, Pain VAS, Patient Global VAS, RAPID3 with sub-domains), medications (RxNorm + dose + frequency + start/stop dates), demographics (age, sex, race, ethnicity, BMI), comorbidities (CCI components or full diagnosis list), wave dates, smoking status, RA disease characteristics (sero-positivity, disease duration, prior biologic count).
- **Format.** CSV with `wave_date` keying. UTF-8, Unix line endings, ISO 8601 dates. One row per (patient × wave × instrument) for PRO; one row per (patient × medication start) for medications.
- **Delivery cadence.** Single batch for first slice, then quarterly refresh.
- **Volume.** ~3,700 RA participants × ~10 historical waves ≈ 35,000 patient-wave records expected. Manageable as a single CSV bundle (estimated < 200 MB compressed).

## Post-call expansions

After the 2026-05-26 call, this directory becomes the canonical source of:
- Adam's confirmed format → `forward_format_spec.md`
- Field availability map (which protocol §4 fields are deliverable as-is, which need derivation, which are unavailable) → `forward_field_spec.md`
- Delivery timeline + transfer mechanism → `forward_delivery_spec.md`
- DUA Option B execution timeline → `dua_status.md`
