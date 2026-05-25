"""cinder.ingest — receiving-side adapters for external data sources.

This package contains the format adapters that convert external data
exports into PTV records validated against ``schemas/ptv_input.schema.json``.

Currently:

* ``forward_webquest_adapter`` — FORWARD WebQuest semi-annual wave exports.
  Stub implementation pending Adam Cornish's 2026-05-26 column-name
  confirmation; column placeholders documented in ``ForwardFieldSpec``
  default values.

Future additions (post-Phase-4.E):

* EHR-direct adapters per institutional partner (UNMC, etc.)
* Mollard 2026 smartphone-signature adapter (Phase 5)

Every adapter in this package follows the same contract:

  ``adapter(...) -> dict[patient_id, ptv_record]``

where each ``ptv_record`` validates against ``schemas/ptv_input.schema.json``
and carries an audited ``metadata.pii_scrubbed`` block so the PII tripwire
permits commits / CI runs that include adapter outputs.
"""
