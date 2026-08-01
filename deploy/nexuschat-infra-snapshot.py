#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path


OUTPUT = Path("/opt/nexuschat/data/infra-snapshot.json")
sys.path.insert(0, "/opt/nexuschat")

from nexus.infra import collect_infra_state


def main() -> None:
    snapshot = collect_infra_state("snapshot")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=".infra-snapshot-", dir=str(OUTPUT.parent)
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(snapshot, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.chmod(temporary, 0o640)
        shutil.chown(temporary, user="nexuschat", group="nexuschat")
        os.replace(temporary, OUTPUT)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


if __name__ == "__main__":
    main()
