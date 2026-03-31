from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path
from typing import Any

from multi_design_spec_loader import design_spec_map, load_design_specs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build compare/detailed HTML from composition_manifest.json."
    )
    parser.add_argument("--job-dir", required=True, help="Multi job directory path")
    parser.add_argument("--batch-range", default=None, help='Optional batch range like "01-05"')
    parser.add_argument("--all-pending", action="store_true", help="Build all pending batches")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def choose_batches(batch_plan: dict[str, Any], batch_range: str | None, all_pending: bool) -> list[dict[str, Any]]:
    batches = batch_plan.get("batches", [])
    if all_pending:
        return [batch for batch in batches if batch.get("status") != "done"]
    if batch_range:
        return [batch for batch in batches if batch.get("range") == batch_range]
    next_batch = batch_plan.get("next_batch")
    if not next_batch or next_batch == "completed":
        return []
    return [batch for batch in batches if batch.get("range") == next_batch]


def analysis_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in payload.get("sections", []) if item.get("id")}


def composition_map(payload: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {item["slot"]: item for item in payload.get("slots", []) if isinstance(item.get("slot"), int)}


def detailed_name(compare_file: str) -> str:
    return compare_file.replace("_compare.html", "_detailed.html")


def relative_to_compare(compare_file: str, target_rel: str) -> str:
    compare_path = Path(compare_file)
    return Path(
        Path("..") / Path("..") / Path(target_rel)
    ).as_posix() if "compare/" in compare_file else target_rel


def product_name(config: dict[str, Any]) -> str:
    return str(config.get("product_info", {}).get("name", "메수스 마사지건"))


def role_copy(role: str, config: dict[str, Any], source_text: str) -> dict[str, Any]:
    name = product_name(config)
    if role == "HOOK":
        return {
            "headline": ["어깨부터 등까지", "손쉽게 닿는", "갈고리형 설계"],
            "body": [name, "휘어진 구조와 12단 진동으로", "손 안 닿는 부위까지 케어"],
        }
    if role == "PAIN":
        return {
            "headline": ["세게만 눌러서", "오래 쓰기 불편한", "일반 안마기"],
            "body": [
                "밀착이 부족하면 시원함이 들쭉날쭉합니다.",
                "손목을 꺾어 써야 해 어깨 뒤쪽이 더 불편합니다.",
                "정작 시원해야 할 등 라인은 혼자 닿기 어렵습니다.",
            ],
        }
    if role == "SOLUTION":
        return {
            "headline": ["끝까지 닿는 구조로", "뭉친 어깨 고민을", "더 편하게 풀어줍니다"],
            "body": [
                "일반 일자형 안마기",
                "손목을 많이 꺾어야 하고 밀착이 일정하지 않을 수 있습니다.",
                "메수스 갈고리형 마사지건",
                "휘어진 구조와 진동 조절로 어깨부터 등까지 안정적으로 관리합니다.",
            ],
        }
    if role == "FEATURE":
        return {
            "headline": ["CHECK POINT"],
            "body": [
                "4종 교체형 헤드",
                "12단 진동 조절",
                "최대 12시간 사용",
            ],
        }
    if role == "BENEFIT":
        return {
            "headline": ["편안하게 들고 쓰는", "초경량 390g"],
            "body": [
                "한 손으로 들고 어깨와 등을 관리할 때도 부담이 적습니다.",
                "부모님도 비교적 편하게 사용할 수 있는 가벼운 무게감입니다.",
            ],
        }
    return {
        "headline": ["뼈대 흐름 유지"],
        "body": [source_text[:48] if source_text else "기존 뼈대 섹션을 유지하는 슬롯입니다."],
    }


def render_skeleton_keep_detailed(order: int, item: dict[str, Any], image_rel: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: #eff1f3; display: flex; justify-content: center; padding: 20px 0; font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif; }}
  .section {{ width: 860px; min-height: 1200px; background: #fff; border-radius: 24px; overflow: hidden; box-shadow: 0 20px 36px rgba(0,0,0,.08); }}
  .hero {{ padding: 28px 34px; background: linear-gradient(135deg, #eef4f6, #fbfbfb); border-bottom: 1px solid rgba(0,0,0,.06); }}
  .tag {{ display: inline-block; padding: 8px 14px; border-radius: 999px; background: #205e5b; color: #fff; font-size: 16px; font-weight: 800; }}
  h1 {{ margin-top: 14px; font-size: 42px; line-height: 1.2; color: #182129; letter-spacing: -.05em; }}
  p {{ margin-top: 12px; font-size: 20px; line-height: 1.7; color: #52606d; }}
  .image-wrap {{ padding: 34px; }}
  .image-wrap img {{ width: 100%; display: block; border-radius: 22px; box-shadow: 0 16px 30px rgba(0,0,0,.08); }}
</style>
</head>
<body>
  <section class="section">
    <div class="hero">
      <div class="tag" contenteditable="true">SKELETON KEEP</div>
      <h1 contenteditable="true">기존 뼈대 슬롯 {order:02d} 유지</h1>
      <p contenteditable="true">이 슬롯은 1번 레퍼런스 흐름을 유지하기 위해 원본 배치를 그대로 살리는 구간입니다. 문구 수정은 최소화하고 톤만 통일하는 기준으로 진행합니다.</p>
    </div>
    <div class="image-wrap">
      <img src="{escape(image_rel)}" alt="skeleton keep {order:02d}">
    </div>
  </section>
</body>
</html>
"""


def render_selected_detailed(role: str, item: dict[str, Any], image_rel: str, config: dict[str, Any], source_text: str, spec: dict[str, Any] | None) -> str:
    copy = role_copy(role, config, source_text)
    if role == "HOOK":
        return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#f4f6f7; display:flex; justify-content:center; padding:20px 0; }}
.section {{ width:860px; height:1550px; position:relative; overflow:hidden; font-family:'Noto Sans KR','Malgun Gothic',sans-serif; }}
.bg {{ position:absolute; inset:0; background:url('{escape(image_rel)}') center/cover no-repeat; }}
.mask {{ position:absolute; top:70px; right:34px; width:360px; height:980px; border-radius:30px; background:linear-gradient(180deg,rgba(255,255,255,.96),rgba(255,255,255,.92)); box-shadow:0 14px 30px rgba(20,40,46,.08); }}
.eyebrow {{ position:absolute; right:86px; top:174px; padding:10px 18px; border-radius:999px; background:#1e6465; color:#fff; font-size:20px; font-weight:800; }}
.headline {{ position:absolute; right:86px; top:254px; width:280px; color:#141b20; font-size:54px; line-height:1.14; letter-spacing:-.07em; font-weight:900; }}
.body {{ position:absolute; right:86px; top:570px; width:280px; color:#41535b; font-size:24px; line-height:1.55; font-weight:700; }}
.list {{ position:absolute; right:86px; top:760px; width:280px; display:grid; gap:12px; }}
.pill {{ padding:14px 16px; border-radius:18px; background:rgba(245,248,249,.98); border:1px solid rgba(22,33,38,.08); color:#20363d; font-size:20px; line-height:1.5; font-weight:700; }}
</style></head><body><section class="section">
<div class="bg"></div><div class="mask"></div>
<div class="eyebrow" contenteditable="true">HOOK</div>
<div class="headline" contenteditable="true">{escape("<br>".join(copy["headline"]))}</div>
<div class="body" contenteditable="true">{escape("<br>".join(copy["body"][:2]))}</div>
<div class="list">
  <div class="pill" contenteditable="true">{escape(copy["body"][0])}</div>
  <div class="pill" contenteditable="true">{escape(copy["body"][1])}</div>
  <div class="pill" contenteditable="true">{escape(copy["body"][2])}</div>
</div></section></body></html>"""
    if role == "PAIN":
        return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#f6f0ec; display:flex; justify-content:center; padding:20px 0; }}
.section {{ width:860px; height:1700px; position:relative; overflow:hidden; font-family:'Noto Sans KR','Malgun Gothic',sans-serif; background:url('{escape(image_rel)}') center/cover no-repeat; }}
.mask {{ position:absolute; left:30px; top:24px; width:800px; height:690px; padding:28px; border-radius:28px; background:linear-gradient(180deg,rgba(255,248,245,.96),rgba(255,248,245,.90)); box-shadow:0 12px 26px rgba(0,0,0,.08); }}
.tag {{ display:inline-block; padding:8px 14px; border-radius:999px; background:#b72f2d; color:#fff; font-size:20px; font-weight:800; }}
h2 {{ margin-top:14px; width:620px; color:#181818; font-size:48px; line-height:1.16; letter-spacing:-.06em; font-weight:900; }}
.bubbles {{ position:absolute; left:36px; right:36px; bottom:110px; display:grid; gap:12px; }}
.bubble {{ padding:18px 20px; border-radius:20px; background:rgba(255,255,255,.94); font-size:22px; line-height:1.55; font-weight:700; color:#2b343a; box-shadow:0 12px 24px rgba(0,0,0,.07); }}
</style></head><body><section class="section">
<div class="mask"><div class="tag" contenteditable="true">PAIN</div><h2 contenteditable="true">{escape("<br>".join(copy["headline"]))}</h2></div>
<div class="bubbles">
<div class="bubble" contenteditable="true">{escape(copy["body"][0])}</div>
<div class="bubble" contenteditable="true">{escape(copy["body"][1])}</div>
<div class="bubble" contenteditable="true">{escape(copy["body"][2])}</div>
</div></section></body></html>"""
    if role == "SOLUTION":
        return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#f4a09a; display:flex; justify-content:center; padding:20px 0; }}
.section {{ width:860px; height:1520px; position:relative; overflow:hidden; font-family:'Noto Sans KR','Malgun Gothic',sans-serif; background:url('{escape(image_rel)}') center/cover no-repeat; }}
.hero {{ position:absolute; left:34px; top:46px; width:792px; height:500px; padding:28px 30px; border-radius:28px; background:linear-gradient(180deg,rgba(226,94,94,.94),rgba(226,94,94,.90)); }}
.tag {{ display:inline-block; padding:10px 18px; border-radius:999px; background:#9c1616; color:#fff; font-size:20px; font-weight:800; }}
h1 {{ margin-top:24px; width:700px; color:#fff; font-size:64px; line-height:1.1; letter-spacing:-.07em; font-weight:900; }}
.compare {{ position:absolute; left:44px; right:44px; bottom:128px; display:grid; grid-template-columns:1fr 1fr; gap:18px; }}
.panel {{ min-height:470px; border-radius:0 0 18px 18px; overflow:hidden; background:rgba(255,255,255,.96); box-shadow:0 16px 28px rgba(0,0,0,.12); }}
.head {{ padding:18px 20px; font-size:23px; line-height:1.4; font-weight:800; color:#fff; }}
.bad {{ background:#6a6a6a; }} .good {{ background:#bc1111; }}
.body {{ padding:24px 20px; display:flex; align-items:flex-end; height:370px; font-size:24px; line-height:1.55; font-weight:700; }}
</style></head><body><section class="section">
<div class="hero"><div class="tag" contenteditable="true">SOLUTION</div><h1 contenteditable="true">{escape("<br>".join(copy["headline"]))}</h1></div>
<div class="compare">
<div class="panel"><div class="head bad" contenteditable="true">{escape(copy["body"][0])}</div><div class="body" style="color:#505050" contenteditable="true">{escape(copy["body"][1])}</div></div>
<div class="panel"><div class="head good" contenteditable="true">{escape(copy["body"][2])}</div><div class="body" style="color:#8f1111" contenteditable="true">{escape(copy["body"][3])}</div></div>
</div></section></body></html>"""
    if role == "FEATURE":
        return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#efefec; display:flex; justify-content:center; padding:20px 0; }}
.section {{ width:860px; height:620px; position:relative; overflow:hidden; font-family:'Noto Sans KR','Malgun Gothic',sans-serif; background:#ececeb; }}
.bg {{ position:absolute; inset:0; background:url('{escape(image_rel)}') center/cover no-repeat; opacity:.18; }}
.title {{ position:absolute; left:0; right:0; top:36px; text-align:center; color:#131821; font-size:58px; line-height:1.2; letter-spacing:-.05em; font-weight:900; }}
.cards {{ position:absolute; left:42px; right:42px; top:206px; display:grid; grid-template-columns:repeat(3,1fr); gap:24px; }}
.card {{ min-height:290px; border-radius:34px; background:rgba(255,255,255,.92); box-shadow:0 16px 30px rgba(0,0,0,.08); display:flex; flex-direction:column; align-items:center; padding:34px 24px 28px; text-align:center; }}
.icon {{ width:112px; height:112px; border-radius:50%; display:flex; align-items:center; justify-content:center; background:#f3f6f8; color:#15202b; font-size:40px; font-weight:900; margin-bottom:24px; }}
.card-title {{ color:#18212b; font-size:28px; line-height:1.35; font-weight:900; }}
</style></head><body><section class="section"><div class="bg"></div>
<div class="title" contenteditable="true">{escape(copy["headline"][0])}</div>
<div class="cards">
<div class="card"><div class="icon">4</div><div class="card-title" contenteditable="true">{escape(copy["body"][0])}</div></div>
<div class="card"><div class="icon">12</div><div class="card-title" contenteditable="true">{escape(copy["body"][1])}</div></div>
<div class="card"><div class="icon">12h</div><div class="card-title" contenteditable="true">{escape(copy["body"][2])}</div></div>
</div></section></body></html>"""
    if role == "BENEFIT":
        return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#fff; display:flex; justify-content:center; padding:20px 0; }}
.section {{ width:860px; height:1280px; position:relative; overflow:hidden; font-family:'Noto Sans KR','Malgun Gothic',sans-serif; background:url('{escape(image_rel)}') center/cover no-repeat; }}
.mask {{ position:absolute; left:88px; right:88px; top:40px; height:320px; padding:22px 18px 12px; background:rgba(255,255,255,.97); border-radius:24px; text-align:center; }}
.point {{ display:inline-block; padding:8px 18px; border-radius:999px; border:2px solid #a5b1b7; color:#58656e; font-size:20px; font-weight:800; }}
.headline {{ margin-top:18px; color:#1a2330; font-size:58px; line-height:1.18; letter-spacing:-.06em; font-weight:900; }}
.headline strong {{ color:#0d6780; }}
.desc {{ margin-top:16px; color:#4a525b; font-size:23px; line-height:1.65; font-weight:700; }}
</style></head><body><section class="section">
<div class="mask"><div class="point" contenteditable="true">POINT 05</div><div class="headline" contenteditable="true">{escape(copy["headline"][0])}<br><strong>{escape(copy["headline"][1])}</strong></div><div class="desc" contenteditable="true">{escape(" ".join(copy["body"]))}</div></div>
</section></body></html>"""
    return render_skeleton_keep_detailed(0, item, image_rel)


def render_compare(order: int, role: str, original_rel: str, detailed_file: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>Multi Detail {order:03d} Compare</title>
<style>
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:#16181d; font-family:'Segoe UI','Malgun Gothic',sans-serif; color:#eef3f8; }}
  .wrap {{ display:flex; gap:14px; padding:14px; }}
  .panel {{ flex:1; background:#222833; border-radius:12px; overflow:hidden; box-shadow:0 10px 28px rgba(0,0,0,.28); }}
  .head {{ padding:12px 16px; font-size:14px; font-weight:800; letter-spacing:.02em; background:#2b3340; }}
  .body {{ height:calc(100vh - 76px); min-height:900px; background:#fff; }}
  .body img, .body iframe {{ width:100%; height:100%; border:0; display:block; }}
  .meta {{ padding:10px 16px; font-size:12px; color:#b8c2cc; background:#1c212a; }}
</style>
</head>
<body>
  <div class="wrap">
    <section class="panel">
      <div class="head">LEFT · ORIGINAL · {order:03d} · {escape(role)}</div>
      <div class="body"><img src="{escape(original_rel)}" alt="original {order:03d}"></div>
      <div class="meta">reference section</div>
    </section>
    <section class="panel">
      <div class="head">RIGHT · RECREATED DETAIL</div>
      <div class="body"><iframe src="{escape(Path(detailed_file).name)}" title="detail {order:03d}"></iframe></div>
      <div class="meta">composition-manifest based recreation</div>
    </section>
  </div>
</body>
</html>
"""


def render_combined(job_id: str, compare_files: list[str]) -> str:
    blocks = []
    for idx, rel in enumerate(compare_files, start=1):
        blocks.append(
            f'<section class="item"><div class="item-head">{idx:02d}</div><iframe src="../{escape(rel)}"></iframe></section>'
        )
    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><title>{escape(job_id)} Combined Review</title><style>
* {{ box-sizing:border-box; }} body {{ margin:0; background:#0f1115; color:#edf2f7; font-family:'Segoe UI','Malgun Gothic',sans-serif; padding:20px; }}
.list {{ display:grid; gap:18px; max-width:1680px; margin:0 auto; }}
.item {{ background:#171b22; border:1px solid rgba(255,255,255,.06); border-radius:16px; overflow:hidden; }}
.item-head {{ padding:12px 16px; background:#1d232d; font-weight:800; }}
iframe {{ width:100%; height:980px; border:0; display:block; background:#101317; }}
</style></head><body><main class="list">{''.join(blocks)}</main></body></html>"""


def main() -> None:
    args = parse_args()
    job_dir = Path(args.job_dir)
    config = load_json(job_dir / "config.json")
    batch_plan = load_json(job_dir / config["analysis_files"].get("batch_plan", "analysis/batch_plan.json"))
    composition = load_json(job_dir / config["analysis_files"].get("composition_manifest", "analysis/composition_manifest.json"))
    section_analysis = load_json(job_dir / config["analysis_files"].get("section_analysis", "analysis/section_analysis.json"))
    design_specs = load_design_specs(job_dir)

    by_slot = composition_map(composition)
    by_analysis = analysis_map(section_analysis)
    by_spec = design_spec_map(design_specs)
    batches = choose_batches(batch_plan, args.batch_range, args.all_pending)

    for batch in batches:
        for item in batch.get("items", []):
            order = int(item["order"])
            slot = by_slot.get(order, {})
            role = str(slot.get("role") or item.get("role") or "")
            image_rel = "../../" + str(slot.get("section_file") or item.get("design_ref_image") or "")
            source_id = str(slot.get("copy_source") or item.get("copy_from") or "")
            source_text = str(by_analysis.get(source_id, {}).get("copy_text", ""))
            spec = by_spec.get(str(slot.get("section_id") or item.get("design_from") or ""))

            detailed_rel = detailed_name(item["compare_file"])
            detailed_path = job_dir / detailed_rel
            compare_path = job_dir / item["compare_file"]
            original_rel = "../../" + str(slot.get("section_file") or item.get("design_ref_image") or "")

            if role == "SKELETON_KEEP":
                detailed_html = render_skeleton_keep_detailed(order, slot, image_rel)
            else:
                detailed_html = render_selected_detailed(role, slot, image_rel, config, source_text, spec)

            write_text(detailed_path, detailed_html)
            write_text(compare_path, render_compare(order, role, original_rel, detailed_rel))
            item["done"] = True

        batch["status"] = "done"

    next_batch = "completed"
    for batch in batch_plan.get("batches", []):
        if batch.get("status") != "done":
            next_batch = batch.get("range")
            break
    batch_plan["next_batch"] = next_batch
    write_text(job_dir / config["analysis_files"].get("batch_plan", "analysis/batch_plan.json"), json.dumps(batch_plan, ensure_ascii=False, indent=2))

    compare_files = []
    for batch in batch_plan.get("batches", []):
        for item in batch.get("items", []):
            if item.get("done"):
                compare_files.append(item["compare_file"])
    write_text(job_dir / config["review_files"].get("combined_review", "review/combined_review.html"), render_combined(config["job_id"], compare_files))

    print(json.dumps({"job_id": config["job_id"], "built_batches": [b["range"] for b in batches], "next_batch": next_batch}, ensure_ascii=False))


if __name__ == "__main__":
    main()
