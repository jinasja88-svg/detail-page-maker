from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path
from typing import Any

from multi_job_manager import build_batch_plan, load_json as load_job_json, update_job_status


CRO_ROLE_ORDER = [
    "HOOK",
    "PAIN",
    "SOLUTION",
    "FEATURE",
    "BENEFIT",
    "SOCIAL_PROOF",
    "INGREDIENT",
    "HOW_TO",
    "COMPARE",
    "BRAND",
    "BUNDLE",
    "GUARANTEE",
    "CTA",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build arrangement.json from best_selection.json and regenerate batch plan."
    )
    parser.add_argument("--job-dir", required=True, help="Multi job directory path")
    parser.add_argument(
        "--selection-file",
        default="analysis/best_selection.json",
        help="Relative path to best selection JSON",
    )
    parser.add_argument(
        "--output-file",
        default="analysis/arrangement.json",
        help="Relative path to arrangement JSON",
    )
    parser.add_argument(
        "--review-file",
        default="review/arrangement_review.html",
        help="Relative path to arrangement review HTML",
    )
    return parser.parse_args()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def role_rank(role: str) -> tuple[int, str]:
    try:
        return (CRO_ROLE_ORDER.index(role), role)
    except ValueError:
        return (len(CRO_ROLE_ORDER), role)


def build_reason(order: int, total: int, role: str) -> str:
    if role == "HOOK":
        return "첫인상에서 관심을 끌기 위해 가장 앞에 배치"
    if role == "PAIN":
        return "고객 고민을 먼저 자극해 다음 해결 섹션으로 연결"
    if role == "SOLUTION":
        return "문제 제기 직후 해결책으로 자연스럽게 전환"
    if role == "CTA":
        return "마지막에 구매 유도 역할로 배치"
    if order == total:
        return "전체 흐름 마무리 단계로 배치"
    return f"CRO 기본 순서에 따라 {role} 역할을 이 위치에 배치"


def render_review_html(job_id: str, arrangement: list[dict[str, Any]]) -> str:
    cards = []
    for item in arrangement:
        cards.append(
            f"""
    <article class="card">
      <div class="order">{item['order']:02d}</div>
      <div class="body">
        <div class="meta">
          <span class="role">{escape(item['role'])}</span>
          <span class="tag">copy {escape(item['copy_from'])}</span>
          <span class="tag">design {escape(item['design_from'])}</span>
        </div>
        <h2>{escape(item['role'])}</h2>
        <p class="reason">{escape(item['reason'])}</p>
      </div>
    </article>
"""
        )

    content = "".join(cards) if cards else '<p class="empty">배열할 섹션이 없습니다.</p>'
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape(job_id)} Arrangement Review</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: 'Segoe UI', 'Malgun Gothic', sans-serif;
    background: #0f1115;
    color: #f5f7fb;
    padding: 28px;
  }}
  .page {{ max-width: 1180px; margin: 0 auto; }}
  .header {{
    margin-bottom: 22px;
    padding: 24px 28px;
    border-radius: 20px;
    background: linear-gradient(135deg, #183a39, #12161c);
  }}
  .list {{
    display: grid;
    gap: 14px;
  }}
  .card {{
    display: grid;
    grid-template-columns: 72px 1fr;
    gap: 16px;
    padding: 18px;
    border-radius: 18px;
    background: #171b22;
    border: 1px solid rgba(255,255,255,0.08);
  }}
  .order {{
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 28px;
    font-weight: 800;
    border-radius: 16px;
    background: #205e5b;
  }}
  .meta {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }}
  .role, .tag {{
    display: inline-block;
    padding: 6px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
  }}
  .role {{ background: #205e5b; }}
  .tag {{ background: #2a303b; color: #cfd7e3; }}
  h2 {{ margin: 0 0 8px; font-size: 22px; }}
  .reason {{ margin: 0; color: #d9e1eb; line-height: 1.7; }}
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
      <h1>{escape(job_id)} Arrangement Review</h1>
      <p>선택된 역할을 CRO 순서로 정렬한 결과입니다. 실제 compare 생성은 이 배열을 기준으로 5개 배치로 진행합니다.</p>
    </section>
    <section class="list">
      {content}
    </section>
  </main>
</body>
</html>
"""


def main() -> None:
    args = parse_args()
    job_dir = Path(args.job_dir)
    config = load_job_json(job_dir / "config.json")
    payload = load_job_json(job_dir / args.selection_file)
    selections = payload.get("selections", [])

    sorted_selections = sorted(selections, key=lambda item: role_rank(item["role"]))
    arrangement = []
    total = len(sorted_selections)
    for order, item in enumerate(sorted_selections, start=1):
        arrangement.append(
            {
                "order": order,
                "role": item["role"],
                "section_id": item["copy_from"],
                "copy_from": item["copy_from"],
                "design_from": item["design_from"],
                "design_ref_image": item.get("design_ref_image", ""),
                "reason": build_reason(order, total, item["role"]),
            }
        )

    output = {"job_id": config["job_id"], "arrangement": arrangement}
    write_json(job_dir / args.output_file, output)
    (job_dir / args.review_file).write_text(
        render_review_html(config["job_id"], arrangement),
        encoding="utf-8",
    )
    build_batch_plan(job_dir, config)
    update_job_status(job_dir, config, "arrangement_complete")
    print(json.dumps(
        {
            "job_id": config["job_id"],
            "arrangement_count": len(arrangement),
            "output_file": args.output_file,
            "review_file": args.review_file,
            "batch_plan_file": config["analysis_files"]["batch_plan"],
        },
        ensure_ascii=False,
    ))


if __name__ == "__main__":
    main()
