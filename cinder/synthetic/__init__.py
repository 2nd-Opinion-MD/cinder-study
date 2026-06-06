"""cinder.synthetic - Track 1 parameterized synthetic patient generator.

Emits FORWARD-export-shaped CSVs (`pro_long`, `medications`, `demographics`) plus
a ground-truth `answer_sheet.json` for the F2 pre-CINDER regression harness. The
cohort is drawn from the literature-cited parameter spec
(`CINDER_synthetic_generator_parameters_v1_1.md`); flares of known class and driver
are planted against M4.A/B/C mechanics so the *real* M4 module can be scored
against the answer sheet downstream. This validates detection MECHANICS
(construct/internal validity), not clinical reality.

Honesty boundary (non-negotiable): output is synthetic and is NEVER represented as
real patient data anywhere - code, filenames, demos, paper, deck. Every emitted
artifact carries a ``synthetic: true`` provenance flag and a parameter-spec
citation. See the package architecture at
`10_Projects/2026_2OPMD/CINDER/answer_sheet_schema_pass/CINDER_Track1_Generator_Architecture_v1_1.md`.
"""

from __future__ import annotations

#: Generator version - stamped into answer-sheet provenance.
GENERATOR_VERSION = "0.1.0-dev"

#: Parameter-spec version this generator draws from (provenance citation).
PARAMETER_SPEC_VERSION = "1.1"

#: Schema target for downstream PTV materialization (no arcs).
SCHEMA_TARGET = "ptv.2.1-indexed-v1-noarcs"

#: Hard honesty flag - present in every emitted artifact's provenance.
SYNTHETIC = True
