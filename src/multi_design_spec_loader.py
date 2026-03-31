from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_design_specs(job_dir: Path) -> dict[str, Any]:
    path = job_dir / "analysis" / "design_specs.json"
    if not path.exists():
        return {"sections": []}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def design_spec_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["section_id"]: item for item in payload.get("sections", []) if item.get("section_id")}
