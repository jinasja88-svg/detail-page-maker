# multi_job_manager 설계

> 기준:
> [멀티_상세페이지_조합_설계.md](D:\Google Drive\코딩_VSCODE\Detail page maker\docs\멀티_상세페이지_조합_설계.md)

> 목적:
> 멀티 상세페이지 조합 작업을 하나의 job으로 생성하고,
> `config.json`, `section_index.json`, `arrangement.json`, `batch_plan.json`까지 이어지는 기준 스키마를 고정한다.

---

## 1. 역할

`multi_job_manager.py`는 아래 역할만 담당한다.

- 멀티 작업 폴더 생성
- 입력 URL/상품 정보 저장
- 각 URL 크롤링 실행
- 각 소스별 이미지 분할 실행
- 섹션 인덱스 생성
- 이후 단계에서 사용할 기본 메타데이터 저장

처음부터 모든 AI 분석까지 넣지 않는다.

---

## 2. CLI 입력 형식

## 권장 실행 예시

```powershell
python src\multi_job_manager.py `
  --job-id multi_job_20260330_001 `
  --product-name "OOO 에센스" `
  --product-target "30대 건성 피부" `
  --feature "72시간 보습 지속" `
  --feature "히알루론산 함유" `
  --strength "끈적임 적음" `
  --strength "레이어링 사용 가능" `
  --source "A|뼈대|https://smartstore.naver.com/aaa/products/111" `
  --source "B|참조|https://smartstore.naver.com/bbb/products/222" `
  --source "C|참조|https://www.coupang.com/vp/products/333" `
  --batch-size 5
```

---

## 3. CLI 인자 제안

| 인자 | 필수 | 설명 |
|------|------|------|
| `--job-id` | 선택 | 지정하지 않으면 날짜 기반 자동 생성 |
| `--product-name` | 필수 | 상품명 |
| `--product-target` | 선택 | 타겟 고객 |
| `--feature` | 선택, 반복 가능 | 상품 특징 |
| `--strength` | 선택, 반복 가능 | 상품 강점 |
| `--source` | 필수, 반복 가능 | `label|role|url` 형식 |
| `--batch-size` | 선택 | 기본값 5 |
| `--output-root` | 선택 | 기본 `output/` |
| `--skip-crawl` | 선택 | 기존 크롤링 결과 재사용 |
| `--skip-split` | 선택 | 기존 sections 재사용 |

---

## 4. source 입력 규칙

### 형식
```text
label|role|url
```

### 예시
```text
A|뼈대|https://smartstore.naver.com/aaa/products/111
B|참조|https://smartstore.naver.com/bbb/products/222
C|참조|https://www.coupang.com/vp/products/333
```

### 규칙
- `label`은 `A`, `B`, `C`처럼 짧고 고유해야 함
- `role`은 `뼈대`, `참조`만 허용
- `뼈대`는 정확히 1개만 허용
- `참조`는 1개 이상 허용
- 전체 source 개수는 2~5개 권장

---

## 5. 출력 디렉터리 구조

```text
output/
  multi_job_20260330_001/
    config.json
    job_status.json
    logs/
    analysis/
      section_index.json
      section_analysis.json
      best_selection.json
      arrangement.json
      batch_plan.json
      copy_variants.json
    review/
      selection_review.html
      arrangement_review.html
      batch_plan.md
      combined_review.html
    sources/
      A_naver_aaa/
        raw/
        detail_images/
        sections/
      B_naver_bbb/
        raw/
        detail_images/
        sections/
      C_coupang_333/
        raw/
        detail_images/
        sections/
    compare/
      batch_01/
      batch_02/
```

---

## 6. config.json 스키마

## 목적
- 이 job의 기준 설정 파일
- 이후 모든 단계가 이 파일을 읽고 경로와 메타데이터를 참조

## 예시

```json
{
  "job_id": "multi_job_20260330_001",
  "created_at": "2026-03-30T15:30:00+09:00",
  "output_root": "output/multi_job_20260330_001",
  "batch_size": 5,
  "product_info": {
    "name": "OOO 에센스",
    "target": "30대 건성 피부",
    "features": [
      "72시간 보습 지속",
      "히알루론산 함유"
    ],
    "strengths": [
      "끈적임 적음",
      "레이어링 사용 가능"
    ]
  },
  "sources": [
    {
      "label": "A",
      "role": "뼈대",
      "url": "https://smartstore.naver.com/aaa/products/111",
      "platform": "naver",
      "slug": "A_naver_aaa",
      "source_dir": "sources/A_naver_aaa",
      "crawl_dir": "sources/A_naver_aaa/detail_images",
      "sections_dir": "sources/A_naver_aaa/sections",
      "detail_count": 0,
      "section_count": 0,
      "status": "pending"
    },
    {
      "label": "B",
      "role": "참조",
      "url": "https://smartstore.naver.com/bbb/products/222",
      "platform": "naver",
      "slug": "B_naver_bbb",
      "source_dir": "sources/B_naver_bbb",
      "crawl_dir": "sources/B_naver_bbb/detail_images",
      "sections_dir": "sources/B_naver_bbb/sections",
      "detail_count": 0,
      "section_count": 0,
      "status": "pending"
    }
  ],
  "analysis_files": {
    "section_index": "analysis/section_index.json",
    "section_analysis": "analysis/section_analysis.json",
    "best_selection": "analysis/best_selection.json",
    "arrangement": "analysis/arrangement.json",
    "batch_plan": "analysis/batch_plan.json",
    "copy_variants": "analysis/copy_variants.json"
  },
  "review_files": {
    "selection_review": "review/selection_review.html",
    "arrangement_review": "review/arrangement_review.html",
    "batch_plan_md": "review/batch_plan.md",
    "combined_review": "review/combined_review.html"
  }
}
```

## 필수 필드

- `job_id`
- `created_at`
- `output_root`
- `batch_size`
- `product_info`
- `sources`

## status 값

- `pending`
- `crawled`
- `split`
- `failed`

---

## 7. section_index.json 스키마

## 목적
- 전체 소스의 섹션을 하나의 인덱스로 모음
- 이후 분석, 선택, 배열 단계는 이 파일을 기준으로 동작

## 예시

```json
{
  "job_id": "multi_job_20260330_001",
  "total_sections": 63,
  "sections": [
    {
      "id": "A_001",
      "source_label": "A",
      "source_role": "뼈대",
      "source_slug": "A_naver_aaa",
      "platform": "naver",
      "section_index": 1,
      "file": "sources/A_naver_aaa/sections/section_001.png"
    },
    {
      "id": "B_001",
      "source_label": "B",
      "source_role": "참조",
      "source_slug": "B_naver_bbb",
      "platform": "naver",
      "section_index": 1,
      "file": "sources/B_naver_bbb/sections/section_001.png"
    }
  ]
}
```

---

## 8. arrangement.json 스키마

## 목적
- 역할별 선택이 끝난 뒤 최종 순서를 확정하는 파일
- 이후 compare 생성과 batch 분할의 기준

## 예시

```json
{
  "job_id": "multi_job_20260330_001",
  "arrangement": [
    {
      "order": 1,
      "role": "HOOK",
      "copy_from": "B_003",
      "design_from": "A_002",
      "design_ref_image": "sources/A_naver_aaa/sections/section_002.png",
      "reason": "숫자형 후킹 카피가 강하고 뼈대와도 잘 맞음"
    },
    {
      "order": 2,
      "role": "PAIN",
      "copy_from": "C_005",
      "design_from": "A_004",
      "design_ref_image": "sources/A_naver_aaa/sections/section_004.png",
      "reason": "고민 나열형 구조가 다음 섹션과 자연스럽게 연결됨"
    }
  ]
}
```

---

## 9. batch_plan.json 스키마

## 목적
- 배열 완료 후 실제 생성/검토를 5개씩 나누는 작업 계획서
- 기존 `compare_batch_manager.py` 철학을 멀티에도 그대로 적용

## 예시

```json
{
  "job_id": "multi_job_20260330_001",
  "batch_size": 5,
  "item_count": 13,
  "batch_count": 3,
  "next_batch": "01-05",
  "batches": [
    {
      "batch_number": 1,
      "range": "01-05",
      "status": "pending",
      "items": [
        {
          "order": 1,
          "role": "HOOK",
          "copy_from": "B_003",
          "design_from": "A_002",
          "compare_file": "compare/batch_01/multi_detail_001_compare.html",
          "done": false
        },
        {
          "order": 2,
          "role": "PAIN",
          "copy_from": "C_005",
          "design_from": "A_004",
          "compare_file": "compare/batch_01/multi_detail_002_compare.html",
          "done": false
        }
      ]
    },
    {
      "batch_number": 2,
      "range": "06-10",
      "status": "pending",
      "items": []
    }
  ]
}
```

## status 값

- `pending`
- `in_progress`
- `done`

## next_batch 규칙

- 첫 미완료 배치를 표시
- 모두 완료되면 `completed`

---

## 10. job_status.json 스키마

## 목적
- 긴 작업의 현재 상태만 빠르게 확인

## 예시

```json
{
  "job_id": "multi_job_20260330_001",
  "current_phase": "phase_1_split_complete",
  "last_updated_at": "2026-03-30T16:00:00+09:00",
  "sources_summary": {
    "total": 3,
    "crawled": 3,
    "split_done": 3,
    "failed": 0
  },
  "analysis_summary": {
    "section_index_created": true,
    "section_analysis_created": false,
    "best_selection_created": false,
    "arrangement_created": false,
    "batch_plan_created": false
  }
}
```

---

## 11. 구현 순서

1. `multi_job_manager.py`에서 CLI 파싱 구현
2. source 문자열 파싱 및 검증
3. job 폴더 구조 생성
4. `config.json` 저장
5. 각 source에 대해 크롤링 실행
6. 각 source에 대해 이미지 분할 실행
7. `section_index.json` 생성
8. `job_status.json` 갱신

여기까지가 1차 목표다.

---

## 12. 검증 포인트

- `뼈대` source가 정확히 1개인지
- `batch_size`가 기본 5로 저장되는지
- 각 source가 고유 `label`을 가지는지
- 크롤링 결과가 source별 폴더로 분리되는지
- `section_index.json`의 `id`가 중복되지 않는지
- 이후 `arrangement.json`이 생기면 `batch_plan.json`으로 정상 분할되는지

---

## 13. 결론

이 설계의 핵심은 두 가지다.

- 멀티 작업도 반드시 하나의 `job`으로 관리한다
- 실제 생성과 검토는 반드시 `batch_size=5` 기준으로 나눈다

즉, `multi_job_manager.py`는 단순 실행 파일이 아니라
멀티 상세페이지 작업 전체의 기준 메타데이터를 만드는 시작점이다.
