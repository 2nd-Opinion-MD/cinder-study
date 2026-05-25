"""Regression tests for the vendored Bayesian kernel layer.

These tests guard against drift in the deterministic Bayesian outputs
produced by ``cinder.bayes`` against fixed inputs. Three layers:

1. ``test_bayes_kernels_unit.py`` — closed-form conjugate updates against
   hand-computed posteriors. Pure-math regression.
2. ``test_bayes_harness_q11_q13.py`` — ports the MVP's q11/q12/q13
   tool-routing assertions into pytest, run against the 632-event real-EHR
   fixture.
3. ``test_bayes_harness_h11_h13.py`` — ports the MVP's h11/h12/h13
   conversational FORWARD-harness questions into pytest, run against the
   same fixture.

All tests are deterministic. No random seeds, no LLM calls, no DB calls
(the MKG retrieval helper returns ``None`` whenever the optional Postgres
DSN is not set, and the kernel falls back to weak priors).
"""
