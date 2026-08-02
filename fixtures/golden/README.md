# Golden anchors FWD-001 / FWD-002

Hand-crafted VAL-2026-003 Phase 1 exit fixtures. Synthetic. Not real patients.

| Anchor | Story | Wave-2 expectation |
|---|---|---|
| FWD-001 | Axiom-visible flare + prednisone within ±90d | `should_detect` |
| FWD-002 | Escalation-absent true flare (PRO MCID, no med anchor) | `axiom_invisible` / UC `widen` |

## F4 variant-0 (CASE-01 / 04 / 06 / 08)

Programmatic goldens from `instantiate_f4_case(case_id, 0)`. Regenerate:

```bash
python scripts/export_f4_golden_fixtures.py
```

| Anchor | Family | Load-bearing wave (0-based) |
|---|---|---|
| CASE-01 | Escalation-absent true flare | wave 2 → `axiom_invisible` |
| CASE-04 | Comorbidity false-positive guard | wave 2 → `comorbidity_driven` / `flag_discordance` |
| CASE-06 | Temporal-sampling failure | wave 2 → `temporal_linkage_missed` |
| CASE-08 | Baseline masking / slow drift | wave 5 → `baseline_masking` |

Provenance seed per case: `f4_seed(case_id, 0)` (910001, 910004, 910006, 910008).

M4.B: HAQ-II ≥ 0.22, PainVAS ≥ 20, PatientGlobalVAS ≥ 20.
field_spec_hash: `9c87cc347e1a24d638bd96ded6ab71d96a8207e15cd757cf172bfc37a081522c`

## FWD-001 wave-2 audit
```json
[
  {
    "wave": 2,
    "delta_haq": 0.3,
    "delta_pain": 25.0,
    "delta_pga": 24.0,
    "domains_crossing_mcid": [
      "HAQ-II",
      "PainVAS",
      "PatientGlobalVAS"
    ],
    "rapid3": 14.4
  },
  {
    "wave": 3,
    "delta_haq": -0.2,
    "delta_pain": -20.0,
    "delta_pga": -20.0,
    "domains_crossing_mcid": [],
    "rapid3": 9.7
  },
  {
    "wave": 4,
    "delta_haq": -0.1,
    "delta_pain": -3.0,
    "delta_pga": -2.0,
    "domains_crossing_mcid": [],
    "rapid3": 8.9
  }
]
```

## FWD-002 wave-2 audit
```json
[
  {
    "wave": 2,
    "delta_haq": 0.3,
    "delta_pain": 23.0,
    "delta_pga": 23.0,
    "domains_crossing_mcid": [
      "HAQ-II",
      "PainVAS",
      "PatientGlobalVAS"
    ],
    "rapid3": 12.3
  },
  {
    "wave": 3,
    "delta_haq": -0.2,
    "delta_pain": -20.0,
    "delta_pga": -20.0,
    "domains_crossing_mcid": [],
    "rapid3": 7.6
  },
  {
    "wave": 4,
    "delta_haq": -0.1,
    "delta_pain": -2.0,
    "delta_pga": -1.0,
    "domains_crossing_mcid": [],
    "rapid3": 7.0
  }
]
```
