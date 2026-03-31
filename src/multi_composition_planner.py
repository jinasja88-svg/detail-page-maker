from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROLE_TO_SLOT = {
    "HOOK": 1,
    "PAIN": 3,
    "SOLUTION": 4,
    "FEATURE": 6,
    "BENEFIT": 10,
    "SOCIAL_PROOF": 14,
    "HOW_TO": 18,
    "COMPARE": 20,
    "CTA": 26,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a baseline multi composition plan using the skeleton length."
    )
    parser.add_argument("--job-dir", required=True, help="Multi job directory path")
    parser.add_argument(
        "--section-index-file",
        default="analysis/section_index.json",
        help="Relative path to section index JSON",
    )
    parser.add_argument(
        "--selection-file",
        default="analysis/best_selection.json",
        help="Relative path to best selection JSON",
    )
    parser.add_argument(
        "--output-file",
        default="analysis/composition_manifest.json",
        help="Relative path to composition manifest JSON",
    )
    parser.add_argument(
        "--image-pool-file",
        default="analysis/image_pool.json",
        help="Relative path to selected image pool JSON",
    )
    parser.add_argument(
        "--recreation-file",
        default="analysis/recreation_plan.json",
        help="Relative path to recreation plan JSON",
    )
    parser.add_argument(
        "--review-file",
        default="review/composition_review.html",
        help="Relative path to composition review HTML",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def source_label(entry: dict[str, Any]) -> str:
    return str(entry.get("source_label") or entry.get("source") or "")


def is_skeleton_source(entry: dict[str, Any]) -> bool:
    role = str(entry.get("role", ""))
    label = str(entry.get("label", ""))
    return label == "A" or role in {"뼈대", "堉덈?"}


def section_order(entry: dict[str, Any]) -> int:
    try:
        return int(entry.get("section_index", 0))
    except (TypeError, ValueError):
        return 0


def render_review_html(job_id: str, manifest: dict[str, Any]) -> str:
    cards = []
    for item in manifest.get("slots", []):
        cards.append(
            f"""
    <article class="card">
      <div class="slot">{item['slot']:02d}</div>
      <div class="body">
        <div class="meta">
          <span class="role">{item['role']}</span>
          <span class="tag">{item['selection_mode']}</span>
        </div>
        <h2>{item['section_id']}</h2>
        <p class="reason">{item['selection_reason']}</p>
        <dl>
          <div><dt>source image</dt><dd>{item['section_file']}</dd></div>
          <div><dt>copy source</dt><dd>{item['copy_source']}</dd></div>
          <div><dt>skeleton slot</dt><dd>{item['skeleton_section_id']}</dd></div>
        </dl>
      </div>
    </article>
"""
        )
    content = "".join(cards)
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{job_id} Composition Review</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 28px; font-family: 'Segoe UI', 'Malgun Gothic', sans-serif; background: #101319; color: #edf2f7; }}
  .page {{ max-width: 1280px; margin: 0 auto; }}
  .header {{ margin-bottom: 20px; padding: 24px 28px; border-radius: 18px; background: linear-gradient(135deg, #183a39, #12161c); }}
  .header h1 {{ margin: 0 0 8px; font-size: 28px; }}
  .header p {{ margin: 0; line-height: 1.7; color: #c8d1da; }}
  .grid {{ display: grid; gap: 14px; }}
  .card {{ display: grid; grid-template-columns: 72px 1fr; gap: 14px; padding: 18px; border-radius: 18px; background: #171b22; border: 1px solid rgba(255,255,255,.08); }}
  .slot {{ display: flex; align-items: center; justify-content: center; border-radius: 14px; background: #205e5b; font-size: 26px; font-weight: 800; }}
  .meta {{ display: flex; gap: 8px; margin-bottom: 10px; }}
  .role, .tag {{ padding: 6px 10px; border-radius: 999px; font-size: 12px; font-weight: 800; }}
  .role {{ background: #2d6776; }}
  .tag {{ background: #2a303b; color: #d1dae5; }}
  h2 {{ margin: 0 0 8px; font-size: 22px; }}
  .reason {{ margin: 0 0 14px; line-height: 1.7; color: #d9e1eb; }}
  dl div {{ display: flex; justify-content: space-between; gap: 12px; padding: 8px 0; border-top: 1px solid rgba(255,255,255,.06); }}
  dt {{ color: #98a5b3; }}
  dd {{ margin: 0; text-align: right; word-break: break-all; }}
</style>
</head>
<body>
  <main class="page">
    <section class="header">
      <h1>{job_id} Composition Review</h1>
      <p>1번 레퍼런스 길이를 기준으로 만든 슬롯 계획입니다. 좋은 장면만 지정 슬롯에 치환하고 나머지는 뼈대 흐름을 유지합니다.</p>
    </section>
    <section class="grid">
      {content}
    </section>
  </main>
</body>
</html>
"""


def main() -> None:
    args = parse_args()
    job_dir = Path(args.job_dir)
    config = load_json(job_dir / "config.json")
    section_index = load_json(job_dir / args.section_index_file)
    selections = load_json(job_dir / args.selection_file).get("selections", [])

    skeleton_label = next(
        source["label"] for source in config["sources"] if is_skeleton_source(source)
    )
    skeleton_sections = sorted(
        [
            section
            for section in section_index.get("sections", [])
            if source_label(section) == skeleton_label
        ],
        key=section_order,
    )
    if not skeleton_sections:
        raise ValueError("No skeleton sections found in section_index.json")

    selection_by_role = {item["role"]: item for item in selections}
    slot_to_selection = {
        slot: selection_by_role[role]
        for role, slot in ROLE_TO_SLOT.items()
        if role in selection_by_role and slot <= len(skeleton_sections)
    }

    slots: list[dict[str, Any]] = []
    for idx, skeleton_section in enumerate(skeleton_sections, start=1):
        chosen = slot_to_selection.get(idx)
        if chosen:
            section_id = chosen["design_from"]
            section_file = chosen.get("design_ref_image", "")
            copy_source = chosen["copy_from"]
            role = chosen["role"]
            selection_reason = (
                f"{role} 역할 슬롯으로 교체. 디자인은 {chosen['design_from']}, "
                f"문구는 {chosen['copy_from']} 기준."
            )
            mode = "selected"
        else:
            section_id = skeleton_section["id"]
            section_file = skeleton_section["file"]
            copy_source = skeleton_section["id"]
            role = "SKELETON_KEEP"
            selection_reason = "뼈대 흐름 유지용 기본 슬롯."
            mode = "skeleton_keep"

        slots.append(
            {
                "slot": idx,
                "role": role,
                "section_id": section_id,
                "section_file": section_file,
                "copy_source": copy_source,
                "skeleton_section_id": skeleton_section["id"],
                "skeleton_section_file": skeleton_section["file"],
                "selection_mode": mode,
                "selection_reason": selection_reason,
            }
        )

    unique_sections: dict[str, dict[str, Any]] = {}
    for slot in slots:
        unique_sections.setdefault(
            slot["section_id"],
            {
                "section_id": slot["section_id"],
                "role": slot["role"],
                "source_file": slot["section_file"],
                "copy_source": slot["copy_source"],
                "used_in_slots": [],
            },
        )
        unique_sections[slot["section_id"]]["used_in_slots"].append(slot["slot"])

    manifest = {
        "job_id": config["job_id"],
        "workflow_version": "v2_user_reset",
        "target_length": len(skeleton_sections),
        "skeleton_source": skeleton_label,
        "rule_summary": {
            "length_rule": "1번 레퍼런스 섹션 수와 동일한 길이로 생성",
            "selection_rule": "좋은 장면만 골라 슬롯 교체, 나머지는 뼈대 유지",
            "design_rule": "색상과 톤은 1번 레퍼런스 기준으로 통일",
            "copy_rule": "기존 문구 길이와 줄 수를 최대한 유지하며 단어만 변형",
        },
        "slots": slots,
    }

    image_pool = {
        "job_id": config["job_id"],
        "pool_count": len(unique_sections),
        "target_length": len(skeleton_sections),
        "images": list(unique_sections.values()),
    }

    recreation_plan = {
        "job_id": config["job_id"],
        "design_reference_source": skeleton_label,
        "design_reference_sections": [item["id"] for item in skeleton_sections],
        "rules": [
            "모든 복원 이미지는 1번 레퍼런스의 배경톤, 색조, 여백감, 폰트 계층을 기준으로 재해석한다.",
            "원본 문구의 줄 수와 상대 글자수를 먼저 맞춘 뒤 단어만 변형한다.",
            "원본 텍스트 영역은 마스크로 완전히 가리고 새 텍스트만 보이게 한다.",
            "새 텍스트는 원문 대비 글자수 80%~115% 범위를 목표로 한다.",
            "배치는 뼈대 슬롯의 좌표와 정렬을 우선 유지한다.",
        ],
        "copy_length_policy": {
            "headline_lines": "원본과 동일",
            "headline_char_ratio": "0.8~1.1",
            "body_lines": "원본과 동일 또는 -1",
            "body_char_ratio": "0.85~1.15",
            "keyword_swap": "핵심 단어만 교체하고 문장 골격 유지",
        },
    }

    write_json(job_dir / args.output_file, manifest)
    write_json(job_dir / args.image_pool_file, image_pool)
    write_json(job_dir / args.recreation_file, recreation_plan)
    (job_dir / args.review_file).write_text(
        render_review_html(config["job_id"], manifest),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "job_id": config["job_id"],
                "target_length": len(skeleton_sections),
                "selected_slot_count": sum(
                    1 for slot in slots if slot["selection_mode"] == "selected"
                ),
                "output_file": args.output_file,
                "image_pool_file": args.image_pool_file,
                "recreation_file": args.recreation_file,
                "review_file": args.review_file,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
