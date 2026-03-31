from __future__ import annotations

import json
from html import escape
from pathlib import Path
import os
from typing import Any

from PIL import Image

ROOT = Path(r'D:\Google Drive\코딩_VSCODE\Detail page maker')
PLAN_DIR = ROOT / 'output' / 'massagegun_multi_20260330_v3_plan'
ANALYSIS_DIR = PLAN_DIR / 'analysis'
RENDER_DIR = PLAN_DIR / 'layout_rendered_samples'
ASSET_DIR = RENDER_DIR / 'assets'

SOURCE_MAP = {
    'A_004': ROOT / 'output' / 'massagegun_multi_20260330_v2' / 'sources' / 'A_coupang_products' / 'sections' / 'section_004.png',
    'C_010': ROOT / 'output' / 'massagegun_multi_20260330_v2' / 'sources' / 'C_naver_products' / 'sections' / 'section_010.png',
    'C_012': ROOT / 'output' / 'massagegun_multi_20260330_v2' / 'sources' / 'C_naver_products' / 'sections' / 'section_012.png',
    'D_031': ROOT / 'output' / 'brand_naver_com_933073be' / 'sections' / 'section_031.png',
    'A_005': ROOT / 'output' / 'massagegun_multi_20260330_v2' / 'sources' / 'A_coupang_products' / 'sections' / 'section_005.png',
    'A_018': ROOT / 'output' / 'massagegun_multi_20260330_v2' / 'sources' / 'A_coupang_products' / 'sections' / 'section_018.png',
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def crop_assets(section_id: str, spec: dict[str, Any]) -> list[dict[str, Any]]:
    src = SOURCE_MAP[section_id]
    img = Image.open(src)
    cropped = []
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    for block in spec.get('image_blocks', []):
        if block.get('has_embedded_text'):
            continue
        x = int(block['x'])
        y = int(block['y'])
        w = int(block['w'])
        h = int(block['h'])
        out = ASSET_DIR / f"{section_id}_{block['id']}.png"
        img.crop((x, y, x + w, y + h)).save(out)
        block = dict(block)
        block['asset_path'] = out
        cropped.append(block)
    return cropped


def css_background(bg: dict[str, Any]) -> str:
    if bg.get('type') == 'gradient' and bg.get('gradient_css'):
        return bg['gradient_css']
    if bg.get('gradient_css'):
        return bg['gradient_css']
    return bg.get('base_color', '#ffffff')


def render_shape(block: dict[str, Any]) -> str:
    extra = ''
    block_id = str(block.get('id', ''))
    if 'pointer' in block_id:
        extra = 'transform: rotate(45deg);'
    style = (
        f"left:{int(block['x'])}px;top:{int(block['y'])}px;width:{int(block['w'])}px;height:{int(block['h'])}px;"
        f"background:{block.get('fill', 'transparent')};border-radius:{int(block.get('radius', 0))}px;"
        f"border:{block.get('border_css', 'none')};box-shadow:{block.get('shadow_css', 'none')};{extra}"
    )
    return f'<div class="shape {escape(str(block.get("kind", "shape")))}" style="{style}"></div>'


def render_text_block(block: dict[str, Any], asset: dict[str, Any] | None) -> str:
    if asset is None:
        text = block.get('text', '')
    else:
        matches = [item for item in asset.get('text_blocks', []) if item.get('id') == block.get('id')]
        text = matches[0].get('original_text', block.get('text', '')) if matches else block.get('text', '')
    html_text = escape(str(text)).replace('\n', '<br>')
    style = (
        f"left:{int(block['x'])}px;top:{int(block['y'])}px;width:{int(block['w'])}px;height:{int(block['h'])}px;"
        f"font-family:{block.get('font_family_css', "'Noto Sans KR', sans-serif")};"
        f"font-size:{int(block['font_size'])}px;font-weight:{int(block['font_weight'])};"
        f"line-height:{block.get('line_height', 1.2)};letter-spacing:{block.get('letter_spacing', 0)}px;"
        f"text-align:{block.get('align', 'left')};color:{block.get('color', '#111')};"
        f"background:{block.get('background_color', 'transparent')};border-radius:{int(block.get('border_radius', 0))}px;"
        f"padding:{block.get('padding_css', '0')};"
    )
    return f'<div class="text-block {escape(str(block.get("kind", "text")))}" style="{style}" contenteditable="true">{html_text}</div>'


def render_image_block(block: dict[str, Any], detailed_path: Path) -> str:
    rel = Path(os.path.relpath(block['asset_path'], start=detailed_path.parent)).as_posix()
    style = (
        f"left:{int(block['x'])}px;top:{int(block['y'])}px;width:{int(block['w'])}px;height:{int(block['h'])}px;"
        f"object-fit:{block.get('fit', 'contain')};"
    )
    return f'<img class="image-block {escape(str(block.get("kind", "image")))}" style="{style}" src="{escape(rel)}" alt="{escape(str(block.get("id", "image")))}">'


def render_detailed(section_id: str, spec: dict[str, Any], text_assets: dict[str, Any], cropped_blocks: list[dict[str, Any]]) -> str:
    width = int(spec['canvas']['width'])
    height = int(spec['canvas']['height'])
    bg = css_background(spec['background'])
    rendered_shapes = ''.join(render_shape(block) for block in spec.get('shape_blocks', []))
    rendered_images = ''.join(render_image_block(block, RENDER_DIR / f'{section_id}_detailed.html') for block in cropped_blocks)
    rendered_text = ''.join(render_text_block(block, text_assets) for block in spec.get('text_blocks', []))
    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape(section_id)} Detailed</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: #11151b; font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif; padding: 24px; }}
.frame {{ width: {width + 60}px; margin: 0 auto; background: #1b232d; border-radius: 24px; padding: 24px; box-shadow: 0 24px 60px rgba(0,0,0,.28); }}
.canvas {{ position: relative; width: {width}px; height: {height}px; margin: 0 auto; overflow: hidden; border-radius: 8px; background: {bg}; }}
.text-block, .shape, .image-block {{ position: absolute; }}
.image-block {{ display: block; }}
</style>
</head>
<body>
  <section class="frame">
    <div class="canvas">{rendered_shapes}{rendered_images}{rendered_text}</div>
  </section>
</body>
</html>'''


def render_compare(section_id: str, source_image: Path, detailed_file: Path) -> str:
    rel_original = Path(os.path.relpath(source_image, start=detailed_file.parent)).as_posix()
    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape(section_id)} Compare</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: #0f1318; font-family: 'Segoe UI', 'Malgun Gothic', sans-serif; color: #eef2f6; padding: 18px; }}
.wrap {{ max-width: 1760px; margin: 0 auto; display: grid; grid-template-columns: 420px 1fr; gap: 18px; align-items: start; }}
.panel {{ background: #1b232d; border-radius: 18px; overflow: hidden; box-shadow: 0 18px 42px rgba(0,0,0,.28); }}
.head {{ padding: 14px 18px; background: #25303d; font-size: 14px; font-weight: 800; letter-spacing: .02em; }}
.meta {{ padding: 10px 18px; background: #151c24; font-size: 12px; color: #b6c0cc; }}
.body {{ background: #fff; min-height: 900px; }}
.body img, .body iframe {{ display: block; width: 100%; height: 100%; min-height: 900px; border: 0; background: #fff; }}
</style>
</head>
<body>
  <main class="wrap">
    <section class="panel">
      <div class="head">LEFT / ORIGINAL</div>
      <div class="meta">{escape(section_id)} original section</div>
      <div class="body"><img src="{escape(rel_original)}" alt="{escape(section_id)} original"></div>
    </section>
    <section class="panel">
      <div class="head">RIGHT / RECREATED</div>
      <div class="meta">layout spec + text assets based reconstruction</div>
      <div class="body"><iframe src="{escape(detailed_file.name)}" title="{escape(section_id)} detailed"></iframe></div>
    </section>
  </main>
</body>
</html>'''


def main() -> None:
    index = load_json(ANALYSIS_DIR / 'text_assets_index.sample.json')
    results = []
    for item in index['items']:
        section_id = item['section_id']
        spec = load_json(PLAN_DIR / item['layout_spec_file'])
        text_assets = load_json(PLAN_DIR / item['text_assets_file'])
        cropped_blocks = crop_assets(section_id, spec)
        detailed_path = RENDER_DIR / f'{section_id}_detailed.html'
        compare_path = RENDER_DIR / f'{section_id}_compare.html'
        write_text(detailed_path, render_detailed(section_id, spec, text_assets, cropped_blocks))
        write_text(compare_path, render_compare(section_id, SOURCE_MAP[section_id], detailed_path))
        results.append({
            'section_id': section_id,
            'detailed': str(detailed_path),
            'compare': str(compare_path),
        })

    combined_items = ''.join(
        f'<section class="item"><div class="item-head">{escape(r["section_id"])} / compare</div><iframe src="{escape(Path(r["compare"]).name)}"></iframe></section>'
        for r in results
    )
    combined = f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Layout Sample Combined</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: #0d1117; font-family: 'Segoe UI', 'Malgun Gothic', sans-serif; color: #eef2f6; padding: 20px; }}
.list {{ max-width: 1760px; margin: 0 auto; display: grid; gap: 20px; }}
.item {{ background: #141a21; border-radius: 18px; overflow: hidden; border: 1px solid rgba(255,255,255,.06); }}
.item-head {{ padding: 14px 18px; background: #1d2630; font-size: 14px; font-weight: 800; letter-spacing: .02em; }}
iframe {{ width: 100%; height: 1100px; border: 0; display: block; background: #10151b; }}
</style>
</head>
<body><main class="list">{combined_items}</main></body></html>'''
    write_text(RENDER_DIR / 'combined_compare.html', combined)
    print(json.dumps(results, ensure_ascii=False))


if __name__ == '__main__':
    main()
