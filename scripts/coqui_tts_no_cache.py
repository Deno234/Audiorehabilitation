#!/home/deno/miniconda3/envs/coqui-tts/bin/python
"""Coqui TTS wrapper that disables numba cache decorators before importing TTS.

Some WSL/conda installs fail while importing librosa because numba tries to
cache functions from package files without a usable locator. This wrapper keeps
the public Coqui CLI arguments used by the pipeline but runs synthesis through
the Python API after forcing numba decorator cache flags off.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def _disable_numba_cache() -> None:
    import numba

    def wrap_no_cache(func):
        def inner(*args, **kwargs):
            kwargs["cache"] = False
            return func(*args, **kwargs)

        return inner

    numba.jit = wrap_no_cache(numba.jit)
    numba.vectorize = wrap_no_cache(numba.vectorize)
    numba.guvectorize = wrap_no_cache(numba.guvectorize)

    import numba.core.decorators
    import numba.np.ufunc.decorators

    numba.core.decorators.jit = numba.jit
    numba.np.ufunc.decorators.vectorize = numba.vectorize
    numba.np.ufunc.decorators.guvectorize = numba.guvectorize


def main() -> None:
    parser = argparse.ArgumentParser(description="Coqui TTS no-cache wrapper")
    parser.add_argument("--text", required=True)
    parser.add_argument("--model_name", required=True)
    parser.add_argument("--out_path", required=True)
    args = parser.parse_args()

    os.environ.setdefault("TTS_HOME", "/mnt/d/Audiorehabilitation/models/coqui_tts")
    _disable_numba_cache()
    from TTS.api import TTS

    Path(args.out_path).parent.mkdir(parents=True, exist_ok=True)
    TTS(model_name=args.model_name).tts_to_file(text=args.text, file_path=args.out_path)


if __name__ == "__main__":
    main()
