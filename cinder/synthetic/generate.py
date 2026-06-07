"""generate.py - ``python -m cinder.synthetic.generate`` entrypoint.

Thin module wrapper so the generator is runnable as a module; all logic lives in `cli.main`.
"""

from __future__ import annotations

import sys

from cinder.synthetic.cli import main

if __name__ == "__main__":
    sys.exit(main())
