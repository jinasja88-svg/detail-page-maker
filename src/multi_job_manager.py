from __future__ import annotations

import argparse
import asyncio
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from crawler import DetailPageCrawler, detect_platform
from image_splitter import split_all_images


VALID_SOURCE_ROLES = {"뼈대", "참조"}
DEFAULT_BATCH_SIZE = 5


@dataclass(frozen=True)
class SourceInput:
    label: str
    role: str
    url: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create and run a multi detail-page composition job."
    )
    parser.add_argument("--job-id", default=None, help="Optional explicit job id")
    parser.add_argument("--product-name", required=True, help="Product name")
    parser.add_argument("--product-target", default="", help="Target customer description")
    parser.add_argument(
        "--feature",
        action="append",
        default=[],
        help="Repeatable product feature",
    )
    parser.add_argument(
        "--strength",
        action="append",
        default=[],
        help="Repeatable product strength",
    )
    parser.add_argument(
        "--source",
        action="append",
        default=[],
        help='Repeatable source definition in "label|role|url" format',
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Batch size for downstream compare work",
    )
    parser.add_argument(
        "--output-root",
        default=None,
        help="Optional output root, defaults to project output directory",
    )
    parser.add_argument("--proxy", default=None, help="Optional crawler proxy URL")
    parser.add_argument(
        "--skip-crawl",
        action="store_true",
        help="Reuse existing source detail_images directories",
    )
    parser.add_argument(
        "--skip-split",
        action="store_true",
        help="Reuse existing sections directories",
    )
    parser.add_argument(
        "--build-batch-plan-only",
        action="store_true",
        help="Skip crawl/split and only rebuild batch plan from arrangement.json",
    )
    return parser.parse_args()


def parse_source(value: str) -> SourceInput:
    parts = value.split("|", 2)
    if len(parts) != 3:
        raise ValueError(f"Invalid --source value: {value}")

    label, role, url = [part.strip() for part in parts]
    if not label:
        raise ValueError(f"Missing label in --source: {value}")
    if role not in VALID_SOURCE_ROLES:
        raise ValueError(f"Invalid role '{role}' in --source: {value}")
    if not re.match(r"^https?://", url, re.IGNORECASE):
        raise ValueError(f"Invalid url in --source: {value}")
    return SourceInput(label=label, role=role, url=url)


def validate_sources(sources: list[SourceInput]) -> None:
    if len(sources) < 2:
        raise ValueError("At least 2 sources are required")

    labels = [source.label for source in sources]
    if len(labels) != len(set(labels)):
        raise ValueError("Source labels must be unique")

    skeleton_count = sum(1 for source in sources if source.role == "뼈대")
    if skeleton_count != 1:
        raise ValueError("Exactly one source must have role '뼈대'")


def default_output_root() -> Path:
    return Path(__file__).resolve().parent.parent / "output"


def generate_job_id() -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"multi_job_{stamp}"


def sanitize_token(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9가-힣]+", "_", value).strip("_")
    return cleaned or "source"


def make_source_slug(source: SourceInput) -> str:
    parsed = urlparse(source.url)
    platform = detect_platform(source.url)
    path_parts = [part for part in parsed.path.split("/") if part]
    tail = path_parts[1] if len(path_parts) > 1 else path_parts[0] if path_parts else parsed.netloc
    return f"{source.label}_{platform}_{sanitize_token(tail)}"


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def ensure_dirs(job_dir: Path) -> None:
    for rel in ("logs", "analysis", "review", "sources", "compare"):
        (job_dir / rel).mkdir(parents=True, exist_ok=True)


def make_config(
    *,
    job_id: str,
    job_dir: Path,
    batch_size: int,
    product_name: str,
    product_target: str,
    features: list[str],
    strengths: list[str],
    sources: list[SourceInput],
) -> dict[str, Any]:
    source_entries = []
    for source in sources:
        slug = make_source_slug(source)
        source_dir = Path("sources") / slug
        source_entries.append(
            {
                "label": source.label,
                "role": source.role,
                "url": source.url,
                "platform": detect_platform(source.url),
                "slug": slug,
                "source_dir": source_dir.as_posix(),
                "crawl_dir": (source_dir / "detail_images").as_posix(),
                "sections_dir": (source_dir / "sections").as_posix(),
                "detail_count": 0,
                "section_count": 0,
                "status": "pending",
                "error": "",
            }
        )

    return {
        "job_id": job_id,
        "created_at": now_iso(),
        "output_root": job_dir.as_posix(),
        "batch_size": batch_size,
        "product_info": {
            "name": product_name,
            "target": product_target,
            "features": features,
            "strengths": strengths,
        },
        "sources": source_entries,
        "analysis_files": {
            "section_index": "analysis/section_index.json",
            "section_analysis": "analysis/section_analysis.json",
            "best_selection": "analysis/best_selection.json",
            "arrangement": "analysis/arrangement.json",
            "composition_manifest": "analysis/composition_manifest.json",
            "image_pool": "analysis/image_pool.json",
            "recreation_plan": "analysis/recreation_plan.json",
            "batch_plan": "analysis/batch_plan.json",
            "copy_variants": "analysis/copy_variants.json",
        },
        "review_files": {
            "selection_review": "review/selection_review.html",
            "arrangement_review": "review/arrangement_review.html",
            "composition_summary": "review/composition_summary.md",
            "batch_plan_md": "review/batch_plan.md",
            "combined_review": "review/combined_review.html",
        },
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def update_job_status(job_dir: Path, config: dict[str, Any], current_phase: str) -> None:
    sources = config["sources"]
    analysis_files = config.get("analysis_files", {})
    status_payload = {
        "job_id": config["job_id"],
        "current_phase": current_phase,
        "last_updated_at": now_iso(),
        "sources_summary": {
            "total": len(sources),
            "crawled": sum(1 for source in sources if source["status"] in {"crawled", "split"}),
            "split_done": sum(1 for source in sources if source["status"] == "split"),
            "failed": sum(1 for source in sources if source["status"] == "failed"),
        },
        "analysis_summary": {
            "section_index_created": (job_dir / analysis_files.get("section_index", "analysis/section_index.json")).exists(),
            "section_analysis_created": (job_dir / analysis_files.get("section_analysis", "analysis/section_analysis.json")).exists(),
            "best_selection_created": (job_dir / analysis_files.get("best_selection", "analysis/best_selection.json")).exists(),
            "arrangement_created": (job_dir / analysis_files.get("arrangement", "analysis/arrangement.json")).exists(),
            "composition_manifest_created": (job_dir / analysis_files.get("composition_manifest", "analysis/composition_manifest.json")).exists(),
            "image_pool_created": (job_dir / analysis_files.get("image_pool", "analysis/image_pool.json")).exists(),
            "recreation_plan_created": (job_dir / analysis_files.get("recreation_plan", "analysis/recreation_plan.json")).exists(),
            "batch_plan_created": (job_dir / analysis_files.get("batch_plan", "analysis/batch_plan.json")).exists(),
        },
    }
    write_json(job_dir / "job_status.json", status_payload)


def move_crawl_output(result: dict[str, Any], target_dir: Path) -> dict[str, Any]:
    source_dir = Path(result["project_dir"])
    if source_dir.resolve() != target_dir.resolve():
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source_dir), str(target_dir))

    def rel(path_str: str) -> str:
        path = Path(path_str)
        if not path.is_absolute():
            return path.as_posix()
        return path.relative_to(target_dir.parent.parent).as_posix()

    result["project_dir"] = target_dir.as_posix()
    result["detail_html_path"] = rel(str(target_dir / "detail_section.html"))
    result["screenshot_path"] = rel(str(target_dir / "full_page.png"))
    result["detail_images"] = [rel(str(Path(p).name if Path(p).is_relative_to(Path(".")) else target_dir / "detail_images" / Path(p).name)) for p in result.get("detail_images", [])]
    result["main_images"] = [rel(str(Path(p).name if Path(p).is_relative_to(Path(".")) else target_dir / "main_images" / Path(p).name)) for p in result.get("main_images", [])]
    return result


def normalize_crawl_result_paths(job_dir: Path, source_entry: dict[str, Any]) -> None:
    source_dir = job_dir / source_entry["source_dir"]
    detail_dir = source_dir / "detail_images"
    main_dir = source_dir / "main_images"
    crawl_result_path = source_dir / "crawl_result.json"
    if not crawl_result_path.exists():
        return

    payload = load_json(crawl_result_path)
    payload["project_dir"] = source_dir.as_posix()
    payload["detail_html_path"] = (source_dir / "detail_section.html").as_posix()
    payload["screenshot_path"] = (source_dir / "full_page.png").as_posix()
    payload["detail_images"] = [str(path.as_posix()) for path in sorted(detail_dir.glob("detail_*"))]
    payload["main_images"] = [str(path.as_posix()) for path in sorted(main_dir.glob("main_*"))]
    write_json(crawl_result_path, payload)


def count_detail_images(detail_dir: Path) -> int:
    return len([path for path in detail_dir.iterdir() if path.is_file()]) if detail_dir.exists() else 0


def count_sections(sections_dir: Path) -> int:
    return len(sorted(sections_dir.glob("section_*.png"))) if sections_dir.exists() else 0


async def crawl_sources(job_dir: Path, config: dict[str, Any], proxy: str | None) -> dict[str, Any]:
    crawler = DetailPageCrawler(output_dir=(job_dir / "sources").as_posix(), proxy=proxy)
    for source_entry in config["sources"]:
        if source_entry["status"] in {"crawled", "split"}:
            continue

        target_dir = job_dir / source_entry["source_dir"]
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        try:
            result = await crawler.crawl(source_entry["url"])
            project_dir = Path(result["project_dir"])
            if project_dir.resolve() != target_dir.resolve():
                if target_dir.exists():
                    shutil.rmtree(target_dir)
                shutil.move(str(project_dir), str(target_dir))

            normalize_crawl_result_paths(job_dir, source_entry)
            source_entry["detail_count"] = count_detail_images(target_dir / "detail_images")
            source_entry["status"] = "crawled"
            source_entry["error"] = ""
        except Exception as exc:
            source_entry["status"] = "failed"
            source_entry["error"] = str(exc)
            if source_entry["role"] == "뼈대":
                raise
        write_json(job_dir / "config.json", config)
        update_job_status(job_dir, config, "phase_1_crawl_in_progress")
    return config


def split_sources(job_dir: Path, config: dict[str, Any]) -> dict[str, Any]:
    for source_entry in config["sources"]:
        if source_entry["status"] == "failed":
            continue
        if source_entry["status"] == "split":
            continue

        detail_dir = job_dir / source_entry["crawl_dir"]
        sections_dir = job_dir / source_entry["sections_dir"]

        if not detail_dir.exists():
            source_entry["status"] = "failed"
            source_entry["error"] = "detail_images directory not found"
        else:
            split_all_images(detail_dir.as_posix(), sections_dir.as_posix())
            source_entry["detail_count"] = count_detail_images(detail_dir)
            source_entry["section_count"] = count_sections(sections_dir)
            source_entry["status"] = "split"
            source_entry["error"] = ""

        write_json(job_dir / "config.json", config)
        update_job_status(job_dir, config, "phase_1_split_in_progress")
    return config


def build_section_index(job_dir: Path, config: dict[str, Any]) -> dict[str, Any]:
    sections: list[dict[str, Any]] = []
    for source_entry in config["sources"]:
        sections_dir = job_dir / source_entry["sections_dir"]
        if not sections_dir.exists():
            continue

        for index, path in enumerate(sorted(sections_dir.glob("section_*.png")), start=1):
            sections.append(
                {
                    "id": f"{source_entry['label']}_{index:03d}",
                    "source_label": source_entry["label"],
                    "source_role": source_entry["role"],
                    "source_slug": source_entry["slug"],
                    "platform": source_entry["platform"],
                    "section_index": index,
                    "file": path.relative_to(job_dir).as_posix(),
                }
            )

    payload = {
        "job_id": config["job_id"],
        "total_sections": len(sections),
        "sections": sections,
    }
    write_json(job_dir / config["analysis_files"]["section_index"], payload)
    return payload


def load_arrangement(job_dir: Path, config: dict[str, Any]) -> dict[str, Any] | None:
    path = job_dir / config["analysis_files"]["arrangement"]
    if not path.exists():
        return None
    return load_json(path)


def load_composition_manifest(job_dir: Path, config: dict[str, Any]) -> dict[str, Any] | None:
    rel_path = config["analysis_files"].get("composition_manifest", "analysis/composition_manifest.json")
    path = job_dir / rel_path
    if not path.exists():
        return None
    return load_json(path)


def compare_file_for(order: int, batch_number: int) -> str:
    return f"compare/batch_{batch_number:02d}/multi_detail_{order:03d}_compare.html"


def batch_status(items: list[dict[str, Any]]) -> str:
    done_count = sum(1 for item in items if item["done"])
    if done_count == 0:
        return "pending"
    if done_count == len(items):
        return "done"
    return "in_progress"


def render_batch_plan_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# {payload['job_id']} Batch Plan",
        "",
        "## Summary",
        f"- Items: `{payload['item_count']}`",
        f"- Batch size: `{payload['batch_size']}`",
        f"- Batch count: `{payload['batch_count']}`",
        f"- Next batch: `{payload['next_batch']}`",
        "",
        "## Batches",
    ]
    for batch in payload["batches"]:
        lines.append(f"- Batch {batch['batch_number']:02d} `{batch['range']}` `{batch['status']}`")
        for item in batch["items"]:
            mark = "done" if item["done"] else "todo"
            lines.append(
                f"  - `{item['order']:03d}` `{mark}` `{item['role']}` "
                f"`{item['copy_from']}` / `{item['design_from']}`"
            )
    lines.extend(
        [
            "",
            "## Workflow",
            "- Build compare pages in groups of five.",
            "- Regenerate combined review after each batch.",
            "- Do not proceed to the next batch until the current batch is reviewed.",
            "",
        ]
    )
    return "\n".join(lines)


def render_placeholder_combined_review(job_id: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape(job_id)} Combined Review</title>
<style>
body {{
  font-family: 'Segoe UI', 'Malgun Gothic', sans-serif;
  background: #0f1115;
  color: #f5f7fb;
  padding: 32px;
}}
.card {{
  max-width: 960px;
  margin: 0 auto;
  padding: 28px;
  border-radius: 20px;
  background: #171b22;
  border: 1px solid rgba(255,255,255,0.08);
}}
h1 {{ margin-bottom: 12px; }}
p {{ line-height: 1.7; color: #c8d1da; }}
</style>
</head>
<body>
  <section class="card">
    <h1>{escape(job_id)} Combined Review</h1>
    <p>아직 compare HTML이 생성되지 않았습니다. 배열 확정 후 5개 배치 단위로 compare를 생성하면 이 파일을 누적 갱신합니다.</p>
  </section>
</body>
</html>
"""


def build_batch_plan(job_dir: Path, config: dict[str, Any]) -> dict[str, Any] | None:
    composition_payload = load_composition_manifest(job_dir, config)
    if composition_payload is not None:
        items_source = [
            {
                "order": item["slot"],
                "role": item["role"],
                "copy_from": item["copy_source"],
                "design_from": item["section_id"],
                "design_ref_image": item["section_file"],
                "selection_mode": item.get("selection_mode", ""),
            }
            for item in composition_payload.get("slots", [])
        ]
    else:
        arrangement_payload = load_arrangement(job_dir, config)
        if arrangement_payload is None:
            return None
        items_source = arrangement_payload.get("arrangement", [])

    batch_size = config["batch_size"]
    batches = []

    for start in range(0, len(items_source), batch_size):
        items = []
        batch_number = start // batch_size + 1
        batch_items = items_source[start:start + batch_size]
        for item in batch_items:
            order = item["order"]
            compare_file = compare_file_for(order, batch_number)
            compare_path = job_dir / compare_file
            items.append(
                {
                    "order": order,
                    "role": item["role"],
                    "copy_from": item["copy_from"],
                    "design_from": item["design_from"],
                    "design_ref_image": item.get("design_ref_image", ""),
                    "selection_mode": item.get("selection_mode", ""),
                    "compare_file": compare_file,
                    "done": compare_path.exists(),
                }
            )
        batches.append(
            {
                "batch_number": batch_number,
                "range": f"{batch_items[0]['order']:02d}-{batch_items[-1]['order']:02d}",
                "status": batch_status(items),
                "items": items,
            }
        )

    next_batch = "completed"
    for batch in batches:
        if batch["status"] != "done":
            next_batch = batch["range"]
            break

    payload = {
        "job_id": config["job_id"],
        "batch_size": batch_size,
        "item_count": len(items_source),
        "batch_count": len(batches),
        "source_mode": "composition_manifest" if composition_payload is not None else "arrangement",
        "next_batch": next_batch,
        "batches": batches,
    }
    write_json(job_dir / config["analysis_files"]["batch_plan"], payload)
    (job_dir / config["review_files"]["batch_plan_md"]).write_text(
        render_batch_plan_markdown(payload),
        encoding="utf-8",
    )
    return payload


def create_empty_analysis_files(job_dir: Path, config: dict[str, Any]) -> None:
    for key in ("section_analysis", "best_selection", "copy_variants"):
        path = job_dir / config["analysis_files"][key]
        if not path.exists():
            write_json(path, {"job_id": config["job_id"], "items": []})

    arrangement_path = job_dir / config["analysis_files"]["arrangement"]
    if not arrangement_path.exists():
        write_json(arrangement_path, {"job_id": config["job_id"], "arrangement": []})

    composition_path = job_dir / config["analysis_files"].get("composition_manifest", "analysis/composition_manifest.json")
    if not composition_path.exists():
        write_json(
            composition_path,
            {"job_id": config["job_id"], "workflow_version": "v2_user_reset", "slots": []},
        )

    image_pool_path = job_dir / config["analysis_files"].get("image_pool", "analysis/image_pool.json")
    if not image_pool_path.exists():
        write_json(image_pool_path, {"job_id": config["job_id"], "images": []})

    recreation_path = job_dir / config["analysis_files"].get("recreation_plan", "analysis/recreation_plan.json")
    if not recreation_path.exists():
        write_json(recreation_path, {"job_id": config["job_id"], "rules": []})

    combined_path = job_dir / config["review_files"]["combined_review"]
    if not combined_path.exists():
        combined_path.write_text(
            render_placeholder_combined_review(config["job_id"]),
            encoding="utf-8",
        )


async def run_job(args: argparse.Namespace) -> dict[str, Any]:
    source_inputs = [parse_source(value) for value in args.source]
    validate_sources(source_inputs)

    if args.batch_size <= 0:
        raise ValueError("--batch-size must be positive")

    output_root = Path(args.output_root) if args.output_root else default_output_root()
    output_root.mkdir(parents=True, exist_ok=True)
    job_id = args.job_id or generate_job_id()
    job_dir = output_root / job_id
    ensure_dirs(job_dir)

    config_path = job_dir / "config.json"
    if config_path.exists():
        config = load_json(config_path)
    else:
        config = make_config(
            job_id=job_id,
            job_dir=job_dir,
            batch_size=args.batch_size,
            product_name=args.product_name,
            product_target=args.product_target,
            features=args.feature,
            strengths=args.strength,
            sources=source_inputs,
        )
        write_json(config_path, config)

    update_job_status(job_dir, config, "initialized")
    create_empty_analysis_files(job_dir, config)

    if args.build_batch_plan_only:
        batch_plan = build_batch_plan(job_dir, config)
        update_job_status(job_dir, config, "batch_plan_only_complete")
        return {
            "job_id": config["job_id"],
            "job_dir": job_dir.as_posix(),
            "batch_plan_created": batch_plan is not None,
        }

    if not args.skip_crawl:
        config = await crawl_sources(job_dir, config, args.proxy)
        write_json(config_path, config)
        update_job_status(job_dir, config, "phase_1_crawl_complete")

    if not args.skip_split:
        config = split_sources(job_dir, config)
        write_json(config_path, config)
        update_job_status(job_dir, config, "phase_1_split_complete")

    section_index = build_section_index(job_dir, config)
    update_job_status(job_dir, config, "section_index_complete")

    batch_plan = build_batch_plan(job_dir, config)
    update_job_status(job_dir, config, "completed")

    return {
        "job_id": config["job_id"],
        "job_dir": job_dir.as_posix(),
        "source_count": len(config["sources"]),
        "total_sections": section_index["total_sections"],
        "batch_plan_created": batch_plan is not None,
        "batch_plan_file": config["analysis_files"]["batch_plan"] if batch_plan else None,
    }


def main() -> None:
    args = parse_args()
    result = asyncio.run(run_job(args))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
