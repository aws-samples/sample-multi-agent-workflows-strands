"""Write a durable, machine-readable completion marker for a workshop lab."""

import json
from datetime import UTC, datetime
from pathlib import Path


def write_validation_artifact(lab: str, evidence: dict) -> Path:
    """Record that a lab reached its final validated state.

    The artifact is separate from notebook output, so facilitators can verify a
    completed run even when Jupyter has not saved the latest output cells.
    """
    directory = Path("validation")  # relative to the notebook's folder, the kernel's working directory
    directory.mkdir(exist_ok=True)
    path = directory / f"{lab}.json"
    # Write to a temporary file, then rename it over the artifact, so a reader never sees half a file.
    temporary = path.with_suffix(".json.tmp")
    payload = {
        "lab": lab,
        "status": "completed",
        "completed_at": datetime.now(UTC).isoformat(),
        "evidence": evidence,
    }
    # default=str writes values JSON cannot encode, such as a datetime or a Path, as text.
    temporary.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    temporary.replace(path)
    print(f"validation artifact: {path.resolve()}")
    return path
