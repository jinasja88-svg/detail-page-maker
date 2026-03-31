from __future__ import annotations

import argparse
import json
from collections import defaultdict
from html import escape
from pathlib import Path
from typing import Any


EXCLUDED_ROLES = {"FILLER"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Select best sections by role from section_analysis.json."
    )
    parser.add_argument("--job-dir", required=True, help="Multi job directory path")
    parser.add_argument(
        "--analysis-file",
        default="analysis/section_analysis.json",
        help="Relative path to section analysis JSON",
    )
    parser.add_argument(
        "--output-file",
        default="analysis/best_selection.json",
        help="Relative path to best selection JSON",
    )
    parser.add_argument(
        "--review-file",
        default="review/selection_review.html",
        help="Relative path to selection review HTML",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def section_source(section: dict[str, Any]) -> str:
    return str(
        section.get("source")
        or section.get("source_label")
        or section.get("label")
        or ""
    )


def section_order(section: dict[str, Any]) -> int:
    return as_int(
        section.get("section_order", section.get("section_index", 9999)),
        9999,
    )


def copy_sort_key(section: dict[str, Any], skeleton_label: str) -> tuple:
    return (
        as_int(section.get("copy_score", 0)),
        as_int(section.get("design_score", 0)),
        1 if section_source(section) == skeleton_label else 0,
        -section_order(section),
    )


def design_sort_key(section: dict[str, Any], skeleton_label: str) -> tuple:
    return (
        as_int(section.get("design_score", 0)),
        1 if section_source(section) == skeleton_label else 0,
        as_int(section.get("copy_score", 0)),
        -section_order(section),
    )


def build_reason(
    role: str,
    copy_best: dict[str, Any],
    design_best: dict[str, Any],
    skeleton_label: str,
) -> str:
    if copy_best["id"] == design_best["id"]:
        if section_source(copy_best) == skeleton_label:
            return f"{role} 역할에서 뼈대 소스가 카피와 디자인 모두 가장 안정적임"
        return f"{role} 역할에서 동일 섹션이 카피와 디자인 점수 모두 우수함"

    parts = []
    parts.append(
        f"카피는 {copy_best['id']}가 더 강함"
        f"(copy {int(copy_best.get('copy_score', 0))}, design {int(copy_best.get('design_score', 0))})"
    )
    if section_source(design_best) == skeleton_label:
        parts.append(
            f"디자인은 뼈대 {design_best['id']}를 사용해 톤앤매너 통일"
        )
    else:
        parts.append(
            f"디자인은 {design_best['id']}가 더 안정적임"
            f"(design {int(design_best.get('design_score', 0))})"
        )
    return ", ".join(parts)


def infer_design_ref_image(section: dict[str, Any]) -> str:
    return str(section.get("file") or section.get("image") or section.get("design_ref_image") or "")


def render_review_html(job_id: str, selections: list[dict[str, Any]]) -> str:
    cards = []
    for selection in selections:
        cards.append(
            f"""
    <article class="card">
      <div class="meta">
        <span class="role">{escape(selection['role'])}</span>
        <span class="tag">copy {escape(selection['copy_from'])}</span>
        <span class="tag">design {escape(selection['design_from'])}</span>
      </div>
      <h2>{escape(selection['role'])}</h2>
      <p class="copy">{escape(selection.get('copy_text', ''))}</p>
      <dl>
        <div><dt>카피 점수</dt><dd>{selection.get('copy_score', 0)}</dd></div>
        <div><dt>디자인 점수</dt><dd>{selection.get('design_score', 0)}</dd></div>
        <div><dt>디자인 참조</dt><dd>{escape(selection.get('design_ref_image', ''))}</dd></div>
      </dl>
      <p class="reason">{escape(selection.get('reason', ''))}</p>
    </article>
"""
        )

    body = "".join(cards) if cards else '<p class="empty">선택 가능한 섹션이 없습니다.</p>'
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape(job_id)} Selection Review</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: 'Segoe UI', 'Malgun Gothic', sans-serif;
    background: #0f1115;
    color: #f5f7fb;
    padding: 28px;
  }}
  .page {{ max-width: 1280px; margin: 0 auto; }}
  .header {{
    margin-bottom: 22px;
    padding: 24px 28px;
    border-radius: 20px;
    background: linear-gradient(135deg, #183a39, #12161c);
  }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 18px;
  }}
  .card {{
    padding: 20px;
    border-radius: 18px;
    background: #171b22;
    border: 1px solid rgba(255,255,255,0.08);
  }}
  .meta {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }}
  .role, .tag {{
    display: inline-block;
    padding: 6px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
  }}
  .role {{ background: #205e5b; }}
  .tag {{ background: #2a303b; color: #cfd7e3; }}
  h2 {{ margin: 0 0 10px; font-size: 22px; }}
  .copy {{ color: #f5f7fb; line-height: 1.6; min-height: 52px; }}
  dl {{ margin: 16px 0; }}
  dl div {{
    display: flex;
    justify-content: space-between;
    gap: 12px;
    padding: 8px 0;
    border-top: 1px solid rgba(255,255,255,0.06);
  }}
  dt {{ color: #98a5b3; }}
  dd {{ margin: 0; text-align: right; }}
  .reason {{ color: #d9e1eb; line-height: 1.7; }}
  .empty {{
    padding: 24px;
    border-radius: 18px;
    background: #171b22;
  }}
</style>
</head>
<body>
  <main class="page">
    <section class="header">
      <h1>{escape(job_id)} Selection Review</h1>
      <p>역할별 카피 출처와 디자인 출처를 검토하는 단계입니다. 실제 compare 생성은 이 다음 단계에서 5개 배치로 진행합니다.</p>
    </section>
    <section class="grid">
      {body}
    </section>
  </main>
</body>
</html>
"""


def main() -> None:
    args = parse_args()
    job_dir = Path(args.job_dir)
    config = load_json(job_dir / "config.json")
    payload = load_json(job_dir / args.analysis_file)
    sections = payload.get("sections", [])

    skeleton_label = next(
        source["label"] for source in config["sources"] if source["role"] == "뼈대"
    )

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for section in sections:
        role = section.get("role", "")
        if not role or role in EXCLUDED_ROLES:
            continue
        grouped[role].append(section)

    selections: list[dict[str, Any]] = []
    for role in sorted(grouped.keys()):
        candidates = grouped[role]
        copy_best = max(candidates, key=lambda item: copy_sort_key(item, skeleton_label))
        design_best = max(candidates, key=lambda item: design_sort_key(item, skeleton_label))

        selections.append(
            {
                "role": role,
                "copy_from": copy_best["id"],
                "copy_text": copy_best.get("copy_text", ""),
                "copy_score": int(copy_best.get("copy_score", 0)),
                "design_from": design_best["id"],
                "design_score": int(design_best.get("design_score", 0)),
                "design_ref_image": infer_design_ref_image(design_best),
                "reason": build_reason(role, copy_best, design_best, skeleton_label),
                "candidates": [
                    {
                        "id": candidate.get("id"),
                        "source": section_source(candidate),
                        "copy_score": as_int(candidate.get("copy_score", 0)),
                        "design_score": as_int(candidate.get("design_score", 0)),
                    }
                    for candidate in sorted(
                        candidates,
                        key=lambda item: (
                            as_int(item.get("copy_score", 0)) + as_int(item.get("design_score", 0)),
                            as_int(item.get("copy_score", 0)),
                            as_int(item.get("design_score", 0)),
                        ),
                        reverse=True,
                    )
                ],
            }
        )

    output = {"job_id": config["job_id"], "selection_count": len(selections), "selections": selections}
    write_json(job_dir / args.output_file, output)
    (job_dir / args.review_file).write_text(
        render_review_html(config["job_id"], selections),
        encoding="utf-8",
    )
    print(json.dumps(
        {
            "job_id": config["job_id"],
            "selection_count": len(selections),
            "output_file": args.output_file,
            "review_file": args.review_file,
        },
        ensure_ascii=False,
    ))


if __name__ == "__main__":
    main()
