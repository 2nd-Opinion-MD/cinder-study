"""emit_csv.py - write a cohort to the three FORWARD-export-shaped CSVs (§6.1-§6.3).

Column headers and order come exclusively from `field_spec` (never hard-coded), so the
output is bound to Dylan's :class:`ForwardFieldSpec` dataclass. Numeric formatting is
locked to the seed exemplars (C8) via `field_spec.format_score` / `format_dose`. The
generator's contract is CSVs + answer sheet; PTV-noarcs materialization is performed by
Dylan's adapter (arch §2), not here.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable
from datetime import date
from pathlib import Path

from cinder.synthetic import GENERATOR_VERSION, PARAMETER_SPEC_VERSION, SCHEMA_TARGET, SYNTHETIC
from cinder.synthetic import field_spec as fs
from cinder.synthetic.records import PatientRecord

#: Provenance sidecar filename written alongside the CSVs so the FORWARD-shaped exports can
#: never be detached from their synthetic origin (honesty boundary).
PROVENANCE_FILENAME = "SYNTHETIC_PROVENANCE.json"

__all__ = [
    "PROVENANCE_FILENAME",
    "write_cohort_csvs",
    "write_demographics",
    "write_medications",
    "write_pro_long",
    "write_provenance_manifest",
]


def _iso(d: date | None) -> str:
    """ISO date string, or empty for None (ongoing meds carry an empty stop_date)."""
    return "" if d is None else d.isoformat()


def write_pro_long(
    patients: Iterable[PatientRecord], path: Path, spec: fs.ForwardFieldSpec
) -> Path:
    """One row per patient x wave x instrument (§6.1)."""
    cols = fs.pro_long_columns(spec)
    with Path(path).open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for p in patients:
            for wave in p.waves:
                for obs in wave.observations:
                    w.writerow(
                        [
                            p.patient_id,
                            wave.wave_number,
                            wave.wave_date.isoformat(),
                            obs.instrument,
                            fs.format_score(obs.instrument, obs.score),
                        ]
                    )
    return Path(path)


def write_medications(
    patients: Iterable[PatientRecord], path: Path, spec: fs.ForwardFieldSpec
) -> Path:
    """One row per medication record (§6.2). `stop_date` empty when ongoing."""
    cols = fs.medications_columns(spec)
    with Path(path).open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for p in patients:
            for m in p.medications:
                w.writerow(
                    [
                        p.patient_id,
                        m.drug_name,
                        m.rxnorm,
                        fs.format_dose(m.dose),
                        m.dose_unit,
                        m.route,
                        m.start_date.isoformat(),
                        _iso(m.stop_date),
                    ]
                )
    return Path(path)


def write_demographics(
    patients: Iterable[PatientRecord], path: Path, spec: fs.ForwardFieldSpec
) -> Path:
    """One row per patient (§6.3)."""
    cols = fs.demographics_columns(spec)
    with Path(path).open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for p in patients:
            w.writerow(
                [
                    p.patient_id,
                    p.sex,
                    p.ra_seropositivity,
                    p.ra_diagnosis_date.isoformat(),
                ]
            )
    return Path(path)


def write_cohort_csvs(
    patients: list[PatientRecord],
    out_dir: Path,
    spec: fs.ForwardFieldSpec | None = None,
) -> dict[str, Path]:
    """Write all three CSVs into ``out_dir``; return the paths keyed by table name."""
    spec = spec or fs.ForwardFieldSpec()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "pro_long": write_pro_long(patients, out / "pro_long.csv", spec),
        "medications": write_medications(patients, out / "medications.csv", spec),
        "demographics": write_demographics(patients, out / "demographics.csv", spec),
    }
    write_provenance_manifest(out, spec, [p.name for p in paths.values()])
    return paths


def write_provenance_manifest(
    out_dir: Path, spec: fs.ForwardFieldSpec, csv_filenames: list[str]
) -> Path:
    """Stamp the output directory as synthetic (the CSVs themselves stay raw FORWARD shape).

    FORWARD exports are a fixed column contract, so the synthetic flag cannot ride inside the
    CSVs without breaking the adapter (R1). This sidecar carries the provenance instead, so a
    consumer can never mistake the exports for real patient data.
    """
    manifest = {
        "synthetic": SYNTHETIC,
        "warning": "SYNTHETIC DATA - NOT REAL PATIENTS. Literature-parameterized cohort for "
        "detection-mechanics validation only. Never represent as real patient data.",
        "generator_version": GENERATOR_VERSION,
        "parameter_spec_version": PARAMETER_SPEC_VERSION,
        "schema_target": SCHEMA_TARGET,
        "field_spec_hash": fs.field_spec_hash(spec),
        "csv_files": csv_filenames,
    }
    path = Path(out_dir) / PROVENANCE_FILENAME
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
