from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate batch compare scaffold HTML files for a multi detail-page job."
    )
    parser.add_argument("--job-dir", required=True, help="Multi job directory path")
    parser.add_argument(
        "--batch-range",
        default=None,
        help='Optional batch range like "01-05". If omitted, uses next_batch from batch_plan.json',
    )
    parser.add_argument(
        "--all-pending",
        action="store_true",
        help="Generate compare scaffold for every incomplete batch",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def compare_iframe_height(index: int) -> int:
    if index <= 5:
        return 1780
    if index <= 10:
        return 1880
    return 1980


def choose_batch(batch_plan: dict[str, Any], batch_range: str | None, all_pending: bool) -> list[dict[str, Any]]:
    batches = batch_plan.get("batches", [])
    if all_pending:
        return [batch for batch in batches if batch.get("status") != "done"]
    if batch_range:
        for batch in batches:
            if batch.get("range") == batch_range:
                return [batch]
        raise ValueError(f"Batch range not found: {batch_range}")

    next_batch = batch_plan.get("next_batch")
    if not next_batch or next_batch == "completed":
        return []
    for batch in batches:
        if batch.get("range") == next_batch:
            return [batch]
    return []


def copy_variant_map(payload: dict[str, Any]) -> dict[int, dict[str, Any]]:
    variants = payload.get("variants") or payload.get("items") or []
    mapping: dict[int, dict[str, Any]] = {}
    for item in variants:
        order = item.get("order")
        if isinstance(order, int):
            mapping[order] = item
    return mapping


def selection_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    selections = payload.get("selections", [])
    return {item["role"]: item for item in selections if item.get("role")}


def arrangement_map(payload: dict[str, Any]) -> dict[int, dict[str, Any]]:
    arrangement = payload.get("arrangement", [])
    return {item["order"]: item for item in arrangement if isinstance(item.get("order"), int)}


def composition_map(payload: dict[str, Any]) -> dict[int, dict[str, Any]]:
    slots = payload.get("slots", [])
    return {item["slot"]: item for item in slots if isinstance(item.get("slot"), int)}


def stage_copy(order: int, role: str, selection: dict[str, Any] | None, variant: dict[str, Any] | None) -> tuple[str, str]:
    if variant and variant.get("new_copy"):
        headline = str(variant.get("new_copy"))
        subcopy = f"{role} 역할 카피 변형 결과"
        return headline, subcopy

    if selection and selection.get("copy_text"):
        headline = str(selection.get("copy_text"))
        subcopy = f"{role} 역할 원문 추출 카피"
        return headline, subcopy

    return f"{role} 섹션 카피 입력", "API 카피 생성 전 임시 스캐폴드"


def render_compare_html(
    *,
    job_id: str,
    order: int,
    role: str,
    ref_image: str,
    copy_from: str,
    design_from: str,
    headline: str,
    subcopy: str,
) -> str:
    ref_img_html = (
        f'<img src="{escape(ref_image)}" alt="{escape(role)} original reference">'
        if ref_image
        else '<div class="missing">디자인 참조 이미지가 아직 없습니다.</div>'
    )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape(job_id)} Detail {order:03d} Compare</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #111;
    font-family: 'Segoe UI', 'Malgun Gothic', sans-serif;
    color: #111;
    padding: 24px;
  }}
  .compare {{
    max-width: 1600px;
    margin: 0 auto;
    display: grid;
    grid-template-columns: 420px 1fr;
    gap: 24px;
    align-items: start;
  }}
  .panel {{
    background: #fff;
    border-radius: 20px;
    overflow: hidden;
    box-shadow: 0 16px 40px rgba(0,0,0,.18);
  }}
  .panel-head {{
    padding: 14px 18px;
    font-size: 14px;
    font-weight: 800;
    letter-spacing: .02em;
    background: #1f1f1f;
    color: #fff;
  }}
  .ref-wrap {{
    padding: 14px;
    background: #f3f3f3;
  }}
  .ref-wrap img {{
    width: 100%;
    display: block;
    border-radius: 14px;
  }}
  .missing {{
    padding: 32px 18px;
    text-align: center;
    color: #666;
    border: 2px dashed #ccc;
    border-radius: 14px;
    background: #fafafa;
  }}
  .stage {{
    padding: 34px;
    background: #f8f8f6;
  }}
  .artboard {{
    width: 860px;
    min-height: 1400px;
    margin: 0 auto;
    background: linear-gradient(180deg, #fcfcfb 0%, #f3f1ea 100%);
    border-radius: 18px;
    overflow: hidden;
    position: relative;
    box-shadow: inset 0 0 0 1px rgba(0,0,0,0.04);
  }}
  .hero {{
    padding: 72px 72px 42px;
    background: linear-gradient(135deg, rgba(32,94,91,0.10), rgba(255,255,255,0.3));
    border-bottom: 1px solid rgba(0,0,0,0.05);
  }}
  .eyebrow {{
    display: inline-block;
    padding: 8px 14px;
    border-radius: 999px;
    background: #205e5b;
    color: #fff;
    font-size: 14px;
    font-weight: 800;
    letter-spacing: .04em;
    margin-bottom: 18px;
  }}
  .headline {{
    font-size: 42px;
    line-height: 1.28;
    font-weight: 900;
    color: #162126;
  }}
  .subcopy {{
    margin-top: 18px;
    font-size: 20px;
    line-height: 1.7;
    color: #4b5865;
  }}
  .meta {{
    padding: 28px 72px 0;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
  }}
  .meta-card {{
    padding: 16px 18px;
    border-radius: 14px;
    background: #fff;
    border: 1px solid rgba(0,0,0,0.08);
  }}
  .meta-card .label {{
    font-size: 12px;
    font-weight: 800;
    color: #6d7783;
    margin-bottom: 8px;
  }}
  .meta-card .value {{
    font-size: 18px;
    line-height: 1.5;
    color: #162126;
    word-break: break-all;
  }}
  .notes {{
    padding: 28px 72px 72px;
    display: grid;
    gap: 18px;
  }}
  .note {{
    padding: 22px 24px;
    border-radius: 16px;
    background: rgba(255,255,255,0.78);
    border: 1px solid rgba(0,0,0,0.07);
  }}
  .note-title {{
    font-size: 14px;
    font-weight: 800;
    color: #205e5b;
    margin-bottom: 10px;
    letter-spacing: .03em;
  }}
  .note-body {{
    font-size: 18px;
    line-height: 1.75;
    color: #2b3440;
  }}
  [contenteditable]:hover {{
    outline: 2px dashed #4fc3f7;
    outline-offset: 3px;
  }}
  [contenteditable]:focus {{
    outline: 2px solid #4fc3f7;
    outline-offset: 3px;
  }}
</style>
</head>
<body>
<div class="compare">
  <div class="panel">
    <div class="panel-head">Original Reference {order:03d}</div>
    <div class="ref-wrap">{ref_img_html}</div>
  </div>
  <div class="panel">
    <div class="panel-head">HTML Recreation {order:03d}</div>
    <div class="stage">
      <section class="artboard">
        <div class="hero">
          <div class="eyebrow" contenteditable="true">{escape(role)}</div>
          <div class="headline" contenteditable="true">{escape(headline)}</div>
          <div class="subcopy" contenteditable="true">{escape(subcopy)}</div>
        </div>
        <div class="meta">
          <div class="meta-card">
            <div class="label">ORDER</div>
            <div class="value" contenteditable="true">{order:03d}</div>
          </div>
          <div class="meta-card">
            <div class="label">COPY FROM</div>
            <div class="value" contenteditable="true">{escape(copy_from)}</div>
          </div>
          <div class="meta-card">
            <div class="label">DESIGN FROM</div>
            <div class="value" contenteditable="true">{escape(design_from)}</div>
          </div>
        </div>
        <div class="notes">
          <div class="note">
            <div class="note-title">SECTION GOAL</div>
            <div class="note-body" contenteditable="true">이 영역은 {escape(role)} 역할을 수행하는 멀티 상세페이지 스캐폴드입니다. 실제 API 디자인 재현 전까지 구조, 카피, 출처를 검토하는 용도로 사용합니다.</div>
          </div>
          <div class="note">
            <div class="note-title">EDITABLE COPY</div>
            <div class="note-body" contenteditable="true">이 텍스트는 이후 API 결과로 교체하거나, 수동으로 바로 수정할 수 있습니다. 현재는 파이프라인 안정성을 위한 기본 편집 스테이지입니다.</div>
          </div>
          <div class="note">
            <div class="note-title">IMPLEMENTATION NOTE</div>
            <div class="note-body" contenteditable="true">나중에 실제 AI 재현 엔진을 붙일 때는 이 오른쪽 스테이지 HTML만 교체하면 됩니다. 왼쪽 원본 참조와 배치 관리 구조는 그대로 유지합니다.</div>
          </div>
        </div>
      </section>
    </div>
  </div>
</div>
</body>
</html>
"""


def render_combined_html(job_id: str, compare_files: list[str]) -> str:
    nav = "\n".join(
        f'        <a href="#s{index:03d}">{index:03d}</a>'
        for index, _ in enumerate(compare_files, start=1)
    )
    blocks = "\n".join(
        f'    <section class="block" id="s{index:03d}">'
        f'<div class="block-head">{escape(job_id)} Detail {index:03d}</div>'
        f'<iframe src="{escape(path)}" height="{compare_iframe_height(index)}" '
        f'title="{escape(job_id)} detail {index:03d} compare"></iframe></section>'
        for index, path in enumerate(compare_files, start=1)
    )
    end_range = f"{len(compare_files):03d}" if compare_files else "000"
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape(job_id)} 001-{end_range} Combined Review</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Segoe UI', 'Malgun Gothic', sans-serif;
    background: #0f1115;
    color: #f5f7fb;
    padding: 28px;
  }}
  .page {{ max-width: 1680px; margin: 0 auto; }}
  .header {{
    margin-bottom: 24px;
    padding: 24px 28px;
    background: linear-gradient(135deg, #183a39, #12161c);
    border-radius: 20px;
    border: 1px solid rgba(255,255,255,0.08);
  }}
  .header h1 {{ font-size: 28px; margin-bottom: 8px; }}
  .header p {{ color: #c8d1da; line-height: 1.6; }}
  .nav {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 16px; }}
  .nav a {{
    color: #fff;
    text-decoration: none;
    background: #205e5b;
    padding: 10px 14px;
    border-radius: 999px;
    font-size: 14px;
    font-weight: 700;
  }}
  .block {{
    margin-bottom: 26px;
    background: #171b22;
    border-radius: 20px;
    border: 1px solid rgba(255,255,255,0.08);
    overflow: hidden;
  }}
  .block-head {{
    padding: 14px 18px;
    font-size: 15px;
    font-weight: 800;
    letter-spacing: 0.02em;
    background: #202632;
    border-bottom: 1px solid rgba(255,255,255,0.08);
  }}
  iframe {{
    width: 100%;
    border: 0;
    display: block;
    background: #fff;
  }}
</style>
</head>
<body>
  <main class="page">
    <section class="header">
      <h1>{escape(job_id)} 001-{end_range} Combined Review</h1>
      <p>멀티 상세페이지 compare 파일을 배치별로 누적한 검토용 파일입니다. 왼쪽은 원본 참조, 오른쪽은 편집 가능한 HTML 스캐폴드입니다.</p>
      <div class="nav">
{nav}
      </div>
    </section>
{blocks}
  </main>
</body>
</html>
"""


def update_batch_plan_done(batch_plan: dict[str, Any], job_dir: Path) -> dict[str, Any]:
    next_batch = "completed"
    for batch in batch_plan.get("batches", []):
        done_count = 0
        for item in batch.get("items", []):
            compare_path = job_dir / item["compare_file"]
            item["done"] = compare_path.exists()
            if item["done"]:
                done_count += 1
        if done_count == 0:
            batch["status"] = "pending"
        elif done_count == len(batch["items"]):
            batch["status"] = "done"
        else:
            batch["status"] = "in_progress"
        if next_batch == "completed" and batch["status"] != "done":
            next_batch = batch["range"]
    batch_plan["next_batch"] = next_batch
    return batch_plan


def main() -> None:
    args = parse_args()
    job_dir = Path(args.job_dir)
    config = load_json(job_dir / "config.json")
    batch_plan_path = job_dir / config["analysis_files"]["batch_plan"]
    arrangement_path = job_dir / config["analysis_files"]["arrangement"]
    composition_path = job_dir / config["analysis_files"].get("composition_manifest", "analysis/composition_manifest.json")
    selection_path = job_dir / config["analysis_files"]["best_selection"]
    copy_variants_path = job_dir / config["analysis_files"]["copy_variants"]

    batch_plan = load_json(batch_plan_path)
    arrangement_payload = load_json(arrangement_path) if arrangement_path.exists() else {"arrangement": []}
    composition_payload = load_json(composition_path) if composition_path.exists() else {"slots": []}
    selection_payload = load_json(selection_path) if selection_path.exists() else {"selections": []}
    copy_variants_payload = load_json(copy_variants_path) if copy_variants_path.exists() else {"variants": []}

    selected_batches = choose_batch(batch_plan, args.batch_range, args.all_pending)
    arrangement_by_order = arrangement_map(arrangement_payload)
    composition_by_order = composition_map(composition_payload)
    selection_by_role = selection_map(selection_payload)
    variants_by_order = copy_variant_map(copy_variants_payload)

    created_files: list[str] = []
    for batch in selected_batches:
        for item in batch.get("items", []):
            order = int(item["order"])
            arrangement_item = arrangement_by_order.get(order, {})
            composition_item = composition_by_order.get(order, {})
            role = str(
                item.get("role")
                or composition_item.get("role")
                or arrangement_item.get("role")
                or ""
            )
            selection = selection_by_role.get(role)
            variant = variants_by_order.get(order)
            headline, subcopy = stage_copy(order, role, selection, variant)
            compare_rel = item["compare_file"]
            compare_path = job_dir / compare_rel
            compare_path.parent.mkdir(parents=True, exist_ok=True)
            compare_path.write_text(
                render_compare_html(
                    job_id=config["job_id"],
                    order=order,
                    role=role,
                    ref_image=str(
                        item.get("design_ref_image")
                        or composition_item.get("section_file")
                        or arrangement_item.get("design_ref_image", "")
                    ),
                    copy_from=str(
                        item.get("copy_from")
                        or composition_item.get("copy_source")
                        or arrangement_item.get("copy_from", "")
                    ),
                    design_from=str(
                        item.get("design_from")
                        or composition_item.get("section_id")
                        or arrangement_item.get("design_from", "")
                    ),
                    headline=headline,
                    subcopy=subcopy,
                ),
                encoding="utf-8",
            )
            created_files.append(compare_rel)

    batch_plan = update_batch_plan_done(batch_plan, job_dir)
    write_json(batch_plan_path, batch_plan)
    all_compare_files = []
    for batch in batch_plan.get("batches", []):
        for item in batch.get("items", []):
            if item.get("done"):
                all_compare_files.append(item["compare_file"])

    combined_path = job_dir / config["review_files"]["combined_review"]
    combined_path.write_text(
        render_combined_html(config["job_id"], all_compare_files),
        encoding="utf-8",
    )

    print(json.dumps(
        {
            "job_id": config["job_id"],
            "created_compare_count": len(created_files),
            "created_files": created_files,
            "combined_review": config["review_files"]["combined_review"],
            "next_batch": batch_plan.get("next_batch"),
        },
        ensure_ascii=False,
    ))


if __name__ == "__main__":
    main()
