from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import TypeVar


DETAIL_RE = re.compile(r"detail_(\d{3})\.(jpg|jpeg|png|gif)$", re.IGNORECASE)
COMPARE_RE_TEMPLATE = r"{slug}_detail_(\d{{3}})_compare\.html$"
T = TypeVar("T")


@dataclass(frozen=True)
class DetailImage:
    index: int
    name: str
    path: Path


@dataclass(frozen=True)
class ComparePage:
    index: int
    name: str
    path: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate 5-item batch plans and combined review HTML for compare pages."
    )
    parser.add_argument("--crawl-dir", required=True, help="Crawl output directory containing detail_images/")
    parser.add_argument("--compare-dir", required=True, help="Directory containing compare HTML files")
    parser.add_argument("--slug", required=True, help="Prefix used for compare files, for example curigen")
    parser.add_argument("--product-label", required=True, help="Human-readable product label")
    parser.add_argument("--batch-size", type=int, default=5, help="Number of detail images per batch")
    parser.add_argument("--start-index", type=int, default=None, help="Optional first detail index to include")
    parser.add_argument("--end-index", type=int, default=None, help="Optional last detail index to include")
    parser.add_argument(
        "--resume-after-last-done",
        action="store_true",
        help="Use the batch after the highest completed compare page as the next batch",
    )
    parser.add_argument("--combined-file", default=None, help="Output filename for the cumulative combined review HTML")
    parser.add_argument("--plan-md", default=None, help="Output filename for the batch plan markdown")
    parser.add_argument("--plan-json", default=None, help="Output filename for the batch plan json")
    return parser.parse_args()


def find_detail_images(detail_dir: Path) -> list[DetailImage]:
    images: list[DetailImage] = []
    for path in sorted(detail_dir.iterdir()):
        match = DETAIL_RE.match(path.name)
        if not match:
            continue
        images.append(DetailImage(index=int(match.group(1)), name=path.name, path=path))
    return images


def find_compare_pages(compare_dir: Path, slug: str) -> list[ComparePage]:
    pattern = re.compile(COMPARE_RE_TEMPLATE.format(slug=re.escape(slug)), re.IGNORECASE)
    pages: list[ComparePage] = []
    for path in sorted(compare_dir.iterdir()):
        match = pattern.match(path.name)
        if not match:
            continue
        pages.append(ComparePage(index=int(match.group(1)), name=path.name, path=path))
    return pages


def group_batches(details: list[DetailImage], batch_size: int) -> list[list[DetailImage]]:
    return [details[i:i + batch_size] for i in range(0, len(details), batch_size)]


def filter_by_index(items: list[T], start_index: int | None, end_index: int | None) -> list[T]:
    filtered = []
    for item in items:
        index = item.index
        if start_index is not None and index < start_index:
            continue
        if end_index is not None and index > end_index:
            continue
        filtered.append(item)
    return filtered


def batch_status(batch: list[DetailImage], done_indexes: set[int]) -> str:
    indexes = [item.index for item in batch]
    completed = sum(1 for idx in indexes if idx in done_indexes)
    if completed == 0:
        return "pending"
    if completed == len(indexes):
        return "done"
    return "in_progress"


def next_batch_range(
    batches: list[list[DetailImage]],
    done_indexes: set[int],
    resume_after_last_done: bool = False,
) -> str | None:
    if resume_after_last_done and done_indexes:
        highest_done = max(done_indexes)
        for batch in batches:
            if batch[-1].index > highest_done:
                return f"{batch[0].index:03d}-{batch[-1].index:03d}"
        return None

    for batch in batches:
        if batch_status(batch, done_indexes) != "done":
            return f"{batch[0].index:03d}-{batch[-1].index:03d}"
    return None


def build_plan_payload(
    details: list[DetailImage],
    compares: list[ComparePage],
    batch_size: int,
    product_label: str,
    resume_after_last_done: bool,
) -> dict:
    done_indexes = {item.index for item in compares}
    batches = group_batches(details, batch_size)
    payload_batches = []
    for batch_no, batch in enumerate(batches, start=1):
        payload_batches.append(
            {
                "batch_number": batch_no,
                "range": f"{batch[0].index:03d}-{batch[-1].index:03d}",
                "status": batch_status(batch, done_indexes),
                "items": [
                    {
                        "index": item.index,
                        "image": item.name,
                        "compare_file": f"curigen_detail_{item.index:03d}_compare.html",
                        "done": item.index in done_indexes,
                    }
                    for item in batch
                ],
            }
        )

    return {
        "product_label": product_label,
        "detail_count": len(details),
        "compare_count": len(compares),
        "batch_size": batch_size,
        "batch_count": len(batches),
        "next_batch": next_batch_range(batches, done_indexes, resume_after_last_done),
        "batches": payload_batches,
    }


def render_plan_markdown(payload: dict) -> str:
    lines = [
        f"# {payload['product_label']} Compare Batch Plan",
        "",
        "## Summary",
        f"- Detail images: `{payload['detail_count']}`",
        f"- Compare pages created: `{payload['compare_count']}`",
        f"- Batch size: `{payload['batch_size']}`",
        f"- Batch count: `{payload['batch_count']}`",
        f"- Next batch: `{payload['next_batch'] or 'completed'}`",
        "",
        "## Batches",
    ]

    for batch in payload["batches"]:
        lines.append(
            f"- Batch {batch['batch_number']:02d} `{batch['range']}` `{batch['status']}`"
        )
        for item in batch["items"]:
            mark = "done" if item["done"] else "todo"
            lines.append(
                f"  - `{item['index']:03d}` `{mark}` `{item['compare_file']}`"
            )
    lines.append("")
    lines.append("## Workflow")
    lines.append("- Create compare pages in groups of five.")
    lines.append("- Regenerate the cumulative combined review after each batch.")
    lines.append("- Continue with the next incomplete batch until every detail image has a compare page.")
    lines.append("")
    return "\n".join(lines)


def compare_iframe_height(index: int) -> int:
    if index <= 8:
        return 1560
    if index == 9:
        return 820
    if index == 10:
        return 680
    if index == 11:
        return 1580
    if index == 12:
        return 1350
    if index == 13:
        return 900
    if index in {14, 15}:
        return 2260
    if index in {16, 17}:
        return 2500
    if index == 18:
        return 860
    if index == 19:
        return 1360
    if index == 20:
        return 4460
    if index == 21:
        return 1560
    if index == 22:
        return 1380
    if index == 23:
        return 1040
    if index == 24:
        return 1580
    if index == 25:
        return 1480
    return 1600


def render_combined_html(product_label: str, compares: list[ComparePage]) -> str:
    nav = "\n".join(
        f'        <a href="#s{page.index:03d}">{page.index:03d}</a>' for page in compares
    )
    blocks = "\n".join(
        (
            f'    <section class="block" id="s{page.index:03d}">'
            f'<div class="block-head">{escape(product_label)} Detail {page.index:03d}</div>'
            f'<iframe src="{escape(page.name)}" height="{compare_iframe_height(page.index)}" '
            f'title="{escape(product_label)} detail {page.index:03d} compare"></iframe></section>'
        )
        for page in compares
    )
    end_range = f"{compares[-1].index:03d}" if compares else "000"
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape(product_label)} 001-{end_range} Combined Review</title>
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
      <h1>{escape(product_label)} 001-{end_range} Combined Review</h1>
      <p>{escape(product_label)} detail compare pages collected into one cumulative review file. Each section keeps the original image on the left and the HTML recreation on the right.</p>
      <div class="nav">
{nav}
      </div>
    </section>
{blocks}
  </main>
</body>
</html>
"""


def main() -> None:
    args = parse_args()
    crawl_dir = Path(args.crawl_dir)
    compare_dir = Path(args.compare_dir)
    detail_dir = crawl_dir / "detail_images"

    details = filter_by_index(
        find_detail_images(detail_dir),
        args.start_index,
        args.end_index,
    )
    compares = filter_by_index(
        find_compare_pages(compare_dir, args.slug),
        args.start_index,
        args.end_index,
    )

    payload = build_plan_payload(
        details,
        compares,
        args.batch_size,
        args.product_label,
        args.resume_after_last_done,
    )

    combined_name = args.combined_file or f"{args.slug}_combined_review.html"
    plan_md_name = args.plan_md or f"{args.slug}_batch_plan.md"
    plan_json_name = args.plan_json or f"{args.slug}_batch_plan.json"

    (compare_dir / combined_name).write_text(
        render_combined_html(args.product_label, compares),
        encoding="utf-8",
    )
    (compare_dir / plan_md_name).write_text(
        render_plan_markdown(payload),
        encoding="utf-8",
    )
    (compare_dir / plan_json_name).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(
        {
            "combined_file": combined_name,
            "plan_md": plan_md_name,
            "plan_json": plan_json_name,
            "next_batch": payload["next_batch"],
            "compare_count": payload["compare_count"],
            "detail_count": payload["detail_count"],
        },
        ensure_ascii=False,
    ))


if __name__ == "__main__":
    main()
