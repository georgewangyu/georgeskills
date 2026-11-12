from __future__ import annotations

import os
import tempfile
from pathlib import Path


def save_token(token_file: Path, token_json: str) -> None:
    token_file.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=token_file.parent, prefix=f".{token_file.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(token_json)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, token_file)
    except BaseException:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise
