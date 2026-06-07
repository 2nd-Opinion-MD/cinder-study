"""rng.py - deterministic, parallel-safe random streams (C6).

A single top-level seed fixes the entire cohort: same seed -> byte-identical output. Each
patient gets an independent substream via :meth:`numpy.random.SeedSequence.spawn`, so the
RNG draws for patient *k* do not depend on how many draws patients before *k* consumed.
That keeps per-patient generation reproducible AND order-independent (a prerequisite for
future parallel generation without breaking determinism).
"""

from __future__ import annotations

import numpy as np

__all__ = ["CohortRNG"]


class CohortRNG:
    """Top-level seed -> per-patient numpy Generators.

    Usage::

        rng = CohortRNG(seed=42)
        for i in range(n):
            gen = rng.patient(i)   # independent, deterministic substream for patient i
    """

    def __init__(self, seed: int) -> None:
        self.seed = int(seed)
        self._root = np.random.SeedSequence(self.seed)
        self._children: list[np.random.SeedSequence] = []

    def patient(self, index: int) -> np.random.Generator:
        """Return the deterministic Generator for patient ``index`` (0-based).

        Substreams are spawned lazily and cached so repeated access to the same index
        returns a fresh Generator seeded identically (callers that need a clean draw
        sequence re-request the same index).
        """
        if index < 0:
            raise ValueError(f"patient index must be non-negative, got {index}")
        while len(self._children) <= index:
            self._children.append(self._root.spawn(1)[0])
        return np.random.default_rng(self._children[index])

    def top_level(self) -> np.random.Generator:
        """A Generator off the root sequence - for cohort-wide (non-per-patient) draws."""
        return np.random.default_rng(np.random.SeedSequence(self.seed))
