# forward_mock_wave/ — synthetic stand-in for a FORWARD WebQuest export

These three CSVs are **synthetic** stand-in files for the
`cinder.ingest.forward_webquest_adapter` round-trip test
(`tests/unit/test_forward_webquest_adapter.py`). They contain no PHI;
patient native IDs and demographic fields are pure placeholders.

The shape follows the field-list asks in
`docs/PRE_CALL_CHECKLIST.md` §2:

| File | Granularity | Columns |
| --- | --- | --- |
| `pro_long.csv` | one row per patient × wave × instrument | `patient_id, wave_number, wave_date, instrument, score` |
| `medications.csv` | one row per medication record | `patient_id, drug_name, rxnorm, dose, dose_unit, route, start_date, stop_date` |
| `demographics.csv` | one row per patient | `patient_id, sex, ra_seropositivity, ra_diagnosis_date` |

## Mock content

Two synthetic patients, four semi-annual waves each, the four PRO
instruments protocol §4.4 cares about (HAQ-II, PainVAS,
PatientGlobalVAS, RAPID3), plus a couple of medication starts and a
demographics row each. One of the two patients has a corticosteroid
start mid-window so the adapter's `route=oral` path is exercised
(eventual §4.5 maintenance-vs-rescue input).

## Column names

These column names are **placeholders**. They match
`ForwardFieldSpec` defaults; on Wednesday 2026-05-27 (after Adam
Cornish's 2026-05-26 confirmation) we point a new `ForwardFieldSpec`
instance at Adam's real names and the same adapter path absorbs the
real wave.
