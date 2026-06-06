"""ptv_materialize.py - OPTIONAL wrapper: synthetic CSVs -> PTV-noarcs JSON (R6, arch §2).

The generator's contract is CSVs + answer sheet; PTV-noarcs materialization is performed by
Dylan's existing `forward_webquest_adapter`, NOT by a synthetic-specific writer. This thin
wrapper invokes that adapter so the synthetic cohort exercises the exact same ingestion path
the real FORWARD export will, and the F2 harness is runnable end-to-end up to the point where
the (private) real M4 module is invoked.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cinder.ingest.forward_webquest_adapter import ForwardFieldSpec, load_forward_wave_csvs

__all__ = ["materialize_ptv"]


def materialize_ptv(
    csv_paths: dict[str, Path], out_path: Path, spec: ForwardFieldSpec | None = None
) -> Path:
    """Convert the three synthetic CSVs to PTV-noarcs JSON via Dylan's adapter.

    ``csv_paths`` is the mapping returned by `emit_csv.write_cohort_csvs`
    (keys: pro_long / medications / demographics). The synthetic CSVs pass through the
    adapter unchanged - there is no synthetic-specific adapter branch (A1).
    """
    spec = spec or ForwardFieldSpec()
    records: dict[str, dict[str, Any]] = load_forward_wave_csvs(
        pro_long_csv=csv_paths["pro_long"],
        medications_csv=csv_paths["medications"],
        demographics_csv=csv_paths["demographics"],
        spec=spec,
        wave_export_id="synthetic_track1",
    )
    payload = {
        "schema": "ptv.2.1-indexed-v1-noarcs",
        "synthetic": True,
        "records": records,
    }
    out = Path(out_path)
    out.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    return out
