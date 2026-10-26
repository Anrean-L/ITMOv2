from __future__ import annotations

import json
import subprocess
from pathlib import Path


root = Path(__file__).resolve().parents[2]

result = subprocess.run(
    [str(root / "scripts" / "check.sh")],
    cwd=root,
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)

status = "PASSED" if result.returncode == 0 else "FAILED"

output = result.stdout[-6000:]

print(
    json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": (
                    f"Automatic project verification {status}.\n\n{output}"
                ),
            }
        }
    )
)
