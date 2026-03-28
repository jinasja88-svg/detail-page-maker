"""
이미지 섹션 분할기
- 세로로 긴 상세페이지 이미지를 여백 기준으로 섹션별로 분할
- AI 없이 Pillow + numpy만으로 처리
"""

import os
import sys
import numpy as np
from PIL import Image

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


SPLIT_RATIO = 3.0       # 세로/가로 비율이 이 이상이면 분할
MIN_BLANK_HEIGHT = 30    # 여백으로 인식할 최소 높이 (px)
MIN_SECTION_HEIGHT = 500 # 분할 후 최소 섹션 높이 (px)
TOLERANCE = 15           # 색상 편차 허용 범위 (낮을수록 엄격)


def find_split_points(img: Image.Image) -> list[int]:
    """이미지에서 여백(단색 줄) 위치를 찾아 분할 지점을 반환한다."""
    arr = np.array(img.convert("RGB"))
    height = arr.shape[0]

    # 각 가로줄의 색상 편차 (편차 작으면 = 단색 여백)
    row_std = np.mean(np.std(arr, axis=1), axis=1)
    is_blank = row_std < TOLERANCE

    # 연속 여백 구간 찾기
    blank_zones = []
    in_blank = False
    blank_start = 0
    for y in range(height):
        if is_blank[y]:
            if not in_blank:
                blank_start = y
                in_blank = True
        else:
            if in_blank:
                if y - blank_start >= MIN_BLANK_HEIGHT:
                    blank_zones.append((blank_start, y))
                in_blank = False

    # 최소 섹션 높이를 유지하며 분할 지점 선택
    split_points = []
    last = 0
    for start, end in blank_zones:
        if start - last >= MIN_SECTION_HEIGHT:
            mid = (start + end) // 2
            split_points.append(mid)
            last = mid

    return split_points


def split_image(image_path: str, output_dir: str) -> list[str]:
    """
    이미지를 여백 기준으로 분할하여 저장한다.
    비율이 SPLIT_RATIO 미만이면 분할하지 않는다.
    """
    img = Image.open(image_path)
    width, height = img.size
    ratio = height / width

    if ratio < SPLIT_RATIO:
        return [image_path]

    split_points = find_split_points(img)
    if not split_points:
        return [image_path]

    os.makedirs(output_dir, exist_ok=True)
    basename = os.path.splitext(os.path.basename(image_path))[0]

    sections = []
    all_points = [0] + split_points + [height]

    for i in range(len(all_points) - 1):
        y_start = all_points[i]
        y_end = all_points[i + 1]
        if y_end - y_start < 50:
            continue
        section = img.crop((0, y_start, width, y_end))
        filename = f"{basename}_section_{i+1:02d}.png"
        filepath = os.path.join(output_dir, filename)
        section.save(filepath)
        sections.append(filepath)

    return sections


def split_all_images(img_dir: str, output_dir: str) -> list[str]:
    """
    폴더 내 모든 이미지를 분할하여 sections 폴더에 순번으로 저장한다.
    짧은 이미지는 그대로, 긴 이미지만 여백 기준 분할.
    """
    os.makedirs(output_dir, exist_ok=True)
    section_num = 1
    all_sections = []

    for f in sorted(os.listdir(img_dir)):
        path = os.path.join(img_dir, f)
        try:
            img = Image.open(path)
        except Exception:
            continue

        w, h = img.size
        ratio = h / w

        if ratio < SPLIT_RATIO:
            # 분할 불필요 → 그대로
            fname = f"section_{section_num:03d}.png"
            img.save(os.path.join(output_dir, fname))
            all_sections.append(os.path.join(output_dir, fname))
            section_num += 1
        else:
            # 여백 기준 분할
            split_points = find_split_points(img)
            if not split_points:
                fname = f"section_{section_num:03d}.png"
                img.save(os.path.join(output_dir, fname))
                all_sections.append(os.path.join(output_dir, fname))
                section_num += 1
            else:
                all_pts = [0] + split_points + [h]
                for i in range(len(all_pts) - 1):
                    y1, y2 = all_pts[i], all_pts[i + 1]
                    if y2 - y1 < 50:
                        continue
                    section = img.crop((0, y1, w, y2))
                    fname = f"section_{section_num:03d}.png"
                    section.save(os.path.join(output_dir, fname))
                    all_sections.append(os.path.join(output_dir, fname))
                    section_num += 1

    return all_sections


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법:")
        print("  단일 이미지: python image_splitter.py <이미지경로> [출력폴더]")
        print("  폴더 전체:   python image_splitter.py --dir <이미지폴더> [출력폴더]")
        sys.exit(1)

    if sys.argv[1] == "--dir":
        img_dir = sys.argv[2]
        output_dir = sys.argv[3] if len(sys.argv) > 3 else os.path.join(img_dir, "..", "sections")
        sections = split_all_images(img_dir, output_dir)
        print(f"총 {len(sections)}개 섹션 → {output_dir}")
    else:
        image_path = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
            os.path.dirname(image_path), "sections"
        )
        results = split_image(image_path, output_dir)
        print(f"결과: {len(results)}개")
