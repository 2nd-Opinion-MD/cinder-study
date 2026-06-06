"""test_synthetic_columns_contract - the R1 coupling guard.

Asserts that the generator's emitted CSV columns are sourced from (and equal to) the
adapter's :class:`ForwardFieldSpec`, that a synthetic cohort's headers byte-match that
contract, and that a 2-patient run flows through Dylan's `load_forward_wave_csvs`
ingestion path unchanged (arch §2 / Phase-0 checkpoint). If Adam Cornish confirms
different FORWARD field names later, this test fails until the generator + answer sheet
move with the dataclass.
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from cinder.ingest.forward_webquest_adapter import ForwardFieldSpec, load_forward_wave_csvs
from cinder.synthetic import field_spec as fs
from cinder.synthetic.emit_csv import write_cohort_csvs
from cinder.synthetic.records import MedEvent, PatientRecord, PROObservation, Wave


def _two_patient_cohort() -> list[PatientRecord]:
    """Minimal 2-patient cohort exercising all three CSVs and every instrument."""
    patients: list[PatientRecord] = []
    for n in (1, 2):
        waves = []
        for w in range(4):
            wave_date = date(2024, 1, 15)
            base = 0.5 + 0.1 * w + 0.2 * (n - 1)
            waves.append(
                Wave(
                    wave_number=w,
                    wave_date=date(wave_date.year + w // 2, 1 + 6 * (w % 2), 15),
                    observations=[
                        PROObservation("HAQ-II", base),
                        PROObservation("PainVAS", 30 + 10 * w),
                        PROObservation("PatientGlobalVAS", 28 + 9 * w),
                        PROObservation("RAPID3", 2.4 + w),
                    ],
                )
            )
        patients.append(
            PatientRecord(
                patient_id=f"SYN-{n:06d}",
                sex="F" if n == 1 else "M",
                ra_seropositivity="seropositive" if n == 1 else "seronegative",
                ra_diagnosis_date=date(2018, 9, 12),
                waves=waves,
                medications=[
                    MedEvent("methotrexate", "8261", 15.0, "mg", "oral", date(2019, 3, 1), None),
                    MedEvent(
                        "prednisone",
                        "8640",
                        10.0,
                        "mg",
                        "oral",
                        date(2024, 8, 2),
                        date(2024, 9, 15),
                    ),
                ],
            )
        )
    return patients


def test_column_helpers_match_dataclass() -> None:
    spec = ForwardFieldSpec()
    assert fs.pro_long_columns(spec) == [
        "patient_id",
        "wave_number",
        "wave_date",
        "instrument",
        "score",
    ]
    assert fs.medications_columns(spec) == [
        "patient_id",
        "drug_name",
        "rxnorm",
        "dose",
        "dose_unit",
        "route",
        "start_date",
        "stop_date",
    ]
    assert fs.demographics_columns(spec) == [
        "patient_id",
        "sex",
        "ra_seropositivity",
        "ra_diagnosis_date",
    ]


def test_emitted_headers_match_field_spec(tmp_path: Path) -> None:
    spec = ForwardFieldSpec()
    paths = write_cohort_csvs(_two_patient_cohort(), tmp_path, spec)
    expected = {
        "pro_long": fs.pro_long_columns(spec),
        "medications": fs.medications_columns(spec),
        "demographics": fs.demographics_columns(spec),
    }
    for name, path in paths.items():
        with path.open(encoding="utf-8") as fh:
            header = next(csv.reader(fh))
        assert header == expected[name], f"{name}.csv header drifted from ForwardFieldSpec"


def test_score_formatting_locked_to_seed() -> None:
    # C8: HAQ-II 1dp; PainVAS/PGA whole-unit ".0"; RAPID3 1dp.
    assert fs.format_score("HAQ-II", 1.14) == "1.1"
    assert fs.format_score("PainVAS", 72.0) == "72.0"
    assert fs.format_score("PatientGlobalVAS", 68.4) == "68.0"
    assert fs.format_score("RAPID3", 18.5) == "18.5"
    assert fs.format_dose(15) == "15.0"


def test_two_patient_run_ingests_through_adapter(tmp_path: Path) -> None:
    spec = ForwardFieldSpec()
    paths = write_cohort_csvs(_two_patient_cohort(), tmp_path, spec)
    records = load_forward_wave_csvs(
        pro_long_csv=paths["pro_long"],
        medications_csv=paths["medications"],
        demographics_csv=paths["demographics"],
        spec=spec,
        wave_export_id="synthetic_contract_smoke",
    )
    # Adapter returns one PTV record per patient, keyed by deterministic UUID.
    assert len(records) == 2


def test_field_spec_hash_is_deterministic() -> None:
    spec = ForwardFieldSpec()
    assert fs.field_spec_hash(spec) == fs.field_spec_hash(ForwardFieldSpec())
    assert len(fs.field_spec_hash(spec)) == 64  # sha256 hex
