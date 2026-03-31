from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build 5-item compare/detailed review files from ordered_plan_v2.json."
    )
    parser.add_argument("--plan-dir", required=True, help="Directory containing ordered_plan_v2.json")
    parser.add_argument("--batch-size", type=int, default=5, help="Number of slots per batch")
    parser.add_argument("--batch-range", default=None, help='Optional batch range like "01-05"')
    parser.add_argument(
        "--source-root",
        action="append",
        default=[],
        help='Source root mapping like "A=output/.../sections"',
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def parse_source_roots(values: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Invalid --source-root value: {value}")
        key, raw_path = value.split("=", 1)
        mapping[key.strip()] = raw_path.strip().replace("\\", "/")
    return mapping


def build_batch_plan(ordered_slots: list[dict[str, Any]], batch_size: int) -> dict[str, Any]:
    batches: list[dict[str, Any]] = []
    for start in range(0, len(ordered_slots), batch_size):
        items = ordered_slots[start : start + batch_size]
        first_slot = int(items[0]["slot"])
        last_slot = int(items[-1]["slot"])
        batches.append(
            {
                "range": f"{first_slot:02d}-{last_slot:02d}",
                "status": "pending",
                "items": [
                    {
                        "slot": int(item["slot"]),
                        "section_id": item["section_id"],
                        "source": item["source"],
                        "role": item["role"],
                        "type": item["type"],
                        "done": False,
                    }
                    for item in items
                ],
            }
        )
    return {"batch_size": batch_size, "next_batch": batches[0]["range"] if batches else "completed", "batches": batches}


def choose_batch(batch_plan: dict[str, Any], batch_range: str | None) -> dict[str, Any]:
    if batch_range:
        for batch in batch_plan["batches"]:
            if batch["range"] == batch_range:
                return batch
        raise ValueError(f"Batch range not found: {batch_range}")
    next_batch = batch_plan.get("next_batch")
    if not next_batch or next_batch == "completed":
        raise ValueError("No pending batch found")
    for batch in batch_plan["batches"]:
        if batch["range"] == next_batch:
            return batch
    raise ValueError("next_batch is missing from batch list")


def selection_pool_map(selection_pool: dict[str, Any]) -> dict[str, dict[str, Any]]:
    items = selection_pool.get("items", [])
    return {str(item["section_id"]): item for item in items if item.get("section_id")}


def resolve_section_file(
    slot: dict[str, Any],
    selected_by_id: dict[str, dict[str, Any]],
    source_roots: dict[str, str],
) -> str:
    section_id = str(slot["section_id"])
    selected = selected_by_id.get(section_id)
    if selected and selected.get("file"):
        return str(selected["file"]).replace("\\", "/")

    source = str(slot["source"])
    source_root = source_roots.get(source)
    if not source_root:
        raise ValueError(f"Missing source root for source {source}")

    section_num = section_id.split("_", 1)[1]
    return f"{source_root}/section_{section_num}.png"


def relative_target(from_file: Path, target: str) -> str:
    import os

    return Path(os.path.relpath(target, start=from_file.parent)).as_posix()


def render_detailed(slot: dict[str, Any], image_rel: str) -> str:
    slot_num = int(slot["slot"])
    role = escape(str(slot["role"]))
    section_id = escape(str(slot["section_id"]))
    source = escape(str(slot["source"]))
    slot_type = escape(str(slot["type"]))
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Slot {slot_num:03d} Detailed</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #11151b;
    font-family: 'Segoe UI', 'Malgun Gothic', sans-serif;
    padding: 20px;
  }}
  .frame {{
    width: 920px;
    margin: 0 auto;
    background: #f3f4f6;
    border-radius: 24px;
    overflow: hidden;
    box-shadow: 0 24px 60px rgba(0,0,0,.28);
  }}
  .head {{
    padding: 18px 24px;
    background: #1d2630;
    color: #eef4fb;
    display: grid;
    grid-template-columns: repeat(4, auto);
    gap: 12px;
    align-items: center;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: .02em;
  }}
  .badge {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 34px;
    padding: 6px 12px;
    border-radius: 999px;
    background: rgba(255,255,255,.08);
  }}
  .stage {{
    padding: 28px;
    background: linear-gradient(180deg, #eceff2 0%, #f8f8f9 100%);
  }}
  .artboard {{
    width: 860px;
    margin: 0 auto;
    background: #fff;
    border-radius: 18px;
    overflow: hidden;
    box-shadow: 0 12px 30px rgba(24,36,44,.10);
  }}
  .artboard img {{
    display: block;
    width: 100%;
    height: auto;
  }}
</style>
</head>
<body>
  <section class="frame">
    <div class="head">
      <div class="badge">SLOT {slot_num:02d}</div>
      <div class="badge">{role}</div>
      <div class="badge">{source}</div>
      <div class="badge">{slot_type} / {section_id}</div>
    </div>
    <div class="stage">
      <div class="artboard">
        <img src="{escape(image_rel)}" alt="{section_id}">
      </div>
    </div>
  </section>
</body>
</html>
"""


def render_compare(slot: dict[str, Any], original_rel: str, detailed_rel: str) -> str:
    slot_num = int(slot["slot"])
    role = escape(str(slot["role"]))
    source = escape(str(slot["source"]))
    section_id = escape(str(slot["section_id"]))
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Slot {slot_num:03d} Compare</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0f1318;
    font-family: 'Segoe UI', 'Malgun Gothic', sans-serif;
    color: #eef2f6;
    padding: 18px;
  }}
  .wrap {{
    max-width: 1760px;
    margin: 0 auto;
    display: grid;
    grid-template-columns: 420px 1fr;
    gap: 18px;
    align-items: start;
  }}
  .panel {{
    background: #1b232d;
    border-radius: 18px;
    overflow: hidden;
    box-shadow: 0 18px 42px rgba(0,0,0,.28);
  }}
  .head {{
    padding: 14px 18px;
    background: #25303d;
    font-size: 14px;
    font-weight: 800;
    letter-spacing: .02em;
  }}
  .meta {{
    padding: 10px 18px;
    background: #151c24;
    font-size: 12px;
    color: #b6c0cc;
  }}
  .body {{
    background: #fff;
    min-height: 900px;
  }}
  .body img, .body iframe {{
    display: block;
    width: 100%;
    height: 100%;
    min-height: 900px;
    border: 0;
    background: #fff;
  }}
</style>
</head>
<body>
  <main class="wrap">
    <section class="panel">
      <div class="head">LEFT / ORIGINAL</div>
      <div class="meta">slot {slot_num:02d} / {role} / {source} / {section_id}</div>
      <div class="body"><img src="{escape(original_rel)}" alt="{section_id} original"></div>
    </section>
    <section class="panel">
      <div class="head">RIGHT / RECREATED</div>
      <div class="meta">exact baseline rebuild / isolated artboard</div>
      <div class="body"><iframe src="{escape(detailed_rel)}" title="{section_id} detailed"></iframe></div>
    </section>
  </main>
</body>
</html>
"""


def render_combined(batch: dict[str, Any]) -> str:
    items_html = []
    for item in batch["items"]:
        compare_file = f"batch_{batch['range']}/slot_{int(item['slot']):03d}_compare.html"
        items_html.append(
            f'<section class="item"><div class="item-head">SLOT {int(item["slot"]):02d} / {escape(str(item["role"]))}</div><iframe src="../recreate/{escape(compare_file)}"></iframe></section>'
        )
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Batch {escape(batch["range"])} Combined Review</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0d1117;
    font-family: 'Segoe UI', 'Malgun Gothic', sans-serif;
    color: #eef2f6;
    padding: 20px;
  }}
  .list {{
    max-width: 1760px;
    margin: 0 auto;
    display: grid;
    gap: 20px;
  }}
  .item {{
    background: #141a21;
    border-radius: 18px;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,.06);
  }}
  .item-head {{
    padding: 14px 18px;
    background: #1d2630;
    font-size: 14px;
    font-weight: 800;
    letter-spacing: .02em;
  }}
  iframe {{
    width: 100%;
    height: 1040px;
    border: 0;
    display: block;
    background: #10151b;
  }}
</style>
</head>
<body>
  <main class="list">
    {''.join(items_html)}
  </main>
</body>
</html>
"""


def main() -> None:
    args = parse_args()
    plan_dir = Path(args.plan_dir)
    ordered_plan = load_json(plan_dir / "ordered_plan_v2.json")
    selection_pool = load_json(plan_dir / "selection_pool.json")
    source_roots = parse_source_roots(args.source_root)

    batch_plan_path = plan_dir / "recreate_batch_plan.json"
    if batch_plan_path.exists():
        batch_plan = load_json(batch_plan_path)
    else:
        batch_plan = build_batch_plan(ordered_plan["ordered_slots"], args.batch_size)

    batch = choose_batch(batch_plan, args.batch_range)
    selected_by_id = selection_pool_map(selection_pool)

    recreate_dir = plan_dir / "recreate" / f"batch_{batch['range']}"
    for item in batch["items"]:
        slot_num = int(item["slot"])
        image_file = resolve_section_file(item, selected_by_id, source_roots)
        detailed_path = recreate_dir / f"slot_{slot_num:03d}_detailed.html"
        compare_path = recreate_dir / f"slot_{slot_num:03d}_compare.html"

        image_rel_for_detailed = relative_target(detailed_path, image_file)
        detailed_rel_for_compare = detailed_path.name
        image_rel_for_compare = relative_target(compare_path, image_file)

        write_text(detailed_path, render_detailed(item, image_rel_for_detailed))
        write_text(compare_path, render_compare(item, image_rel_for_compare, detailed_rel_for_compare))
        item["done"] = True

    batch["status"] = "done"
    next_batch = "completed"
    for current in batch_plan["batches"]:
        if current["status"] != "done":
            next_batch = current["range"]
            break
    batch_plan["next_batch"] = next_batch

    combined_path = plan_dir / "recreate" / f"combined_review_{batch['range']}.html"
    write_text(combined_path, render_combined(batch))
    write_text(batch_plan_path, json.dumps(batch_plan, ensure_ascii=False, indent=2))

    print(
        json.dumps(
            {
                "plan_dir": str(plan_dir),
                "built_batch": batch["range"],
                "combined_review": str(combined_path),
                "next_batch": next_batch,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
