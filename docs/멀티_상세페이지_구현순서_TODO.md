# 멀티 상세페이지 조합 구현 순서 및 TODO

> 기준 문서:
> [멀티_상세페이지_조합_설계.md](D:\Google Drive\코딩_VSCODE\Detail page maker\docs\멀티_상세페이지_조합_설계.md)

> 원칙:
> 기존 단일 상세페이지 흐름은 유지하고,
> 멀티 상세페이지 조합 기능은 별도 작업 단위와 별도 파일명으로 추가한다.

> 중요:
> 생성과 검토는 반드시 `5개 배치 단위`로 유지한다.
> 멀티 조합이어도 한 번에 전체를 생성하지 않는다.

---

## 1. 현재 상태 요약

### 이미 있는 것
- `crawler.py`
  - 네이버/쿠팡/카페24 크롤링 가능
- `image_splitter.py`
  - 긴 상세이미지 섹션 분할 가능
- `compare_batch_manager.py`
  - 5개 배치 계획 생성
  - 누적 combined review 생성
- 섹션 분석/HTML 재현 방식
  - 단일 섹션 기준 테스트 완료
- 문서
  - 단일 워크플로우와 멀티 조합 설계 초안 존재

### 아직 없는 것
- 멀티 URL 입력을 하나의 작업으로 묶는 실행 진입점
- 멀티 작업용 `config.json` 생성
- 전체 섹션 역할 태깅 결과물 관리
- 역할별 베스트 섹션 선택 로직
- 배열안 리뷰 HTML
- 멀티 소스 기준 compare 생성 방식
- 멀티 작업 상태를 이어서 진행하는 관리 방식

---

## 2. 구현 방향

### 기본 전략
- 기존 모듈은 최대한 재사용
- 멀티용 orchestration만 새로 추가
- 기존 단일 작업 파일명/출력 규칙은 건드리지 않음
- 기존 `5개 배치 작업 방식`을 멀티에서도 그대로 유지

### 새로 추가할 핵심 개념
- `multi_job`
  - 하나의 멀티 상세페이지 작업 단위
- `config.json`
  - URL 목록, 역할, 상품 정보, 출력 경로 기록
- `section_analysis.json`
  - 전체 섹션 역할 태깅 결과
- `best_selection.json`
  - 역할별 선택 결과
- `arrangement.json`
  - 최종 배열 결과
- `batch_plan.json`
  - 배열 기준 5개 배치 작업 계획

---

## 3. 구현 순서

## Step 1. 멀티 작업 디렉터리와 설정 파일부터 만든다

### 목표
- 멀티 작업의 기준 디렉터리 구조를 먼저 고정
- 이후 모든 단계가 같은 폴더 구조를 공유하도록 한다

### 해야 할 일
- 새 스크립트 추가
  - 예: `src/multi_job_manager.py`
- 입력값 정의
  - URL 리스트
  - 각 URL의 label
  - 각 URL의 role (`뼈대`, `참조`)
  - 상품 정보
- 출력 경로 규칙 정의

### 권장 출력 구조
```text
output/
  multi_job_20260330_001/
    config.json
    A_naver_xxx/
      raw/
      detail_images/
      sections/
    B_naver_yyy/
      raw/
      detail_images/
      sections/
    C_coupang_333/
      raw/
      detail_images/
      sections/
    analysis/
      section_analysis.json
      best_selection.json
      arrangement.json
      batch_plan.json
    review/
      selection_review.html
      arrangement_review.html
      batch_plan.md
      combined_review.html
```

### 완료 기준
- URL과 상품 정보를 넣으면 `config.json`만이라도 정상 생성
- 작업 폴더가 자동 생성
- 기본 배치 크기 `5`가 설정값으로 함께 기록

---

## Step 2. 멀티 크롤링 실행 루프를 만든다

### 목표
- URL 3~5개를 하나의 job으로 순차 처리

### 해야 할 일
- `crawler.py`를 직접 수정하기보다
- `multi_job_manager.py`에서 각 URL에 대해 반복 호출
- 각 결과를 소스별 폴더에 저장

### 구현 포인트
- 각 소스별 저장 디렉터리 분리
- 실패한 URL과 성공한 URL 상태 기록
- 뼈대 URL이 실패하면 전체 작업 중단
- 참조 URL 일부 실패는 경고 후 계속 진행 가능

### TODO
- [ ] URL 리스트 입력 포맷 확정
- [ ] 소스별 slug 생성 규칙 정리
- [ ] 크롤링 결과 경로를 `config.json`에 기록
- [ ] 실패/성공 상태 필드 추가

### 완료 기준
- 3개 URL 입력 시 각 소스별 `detail_images/` 생성
- `config.json`에 `crawl_dir`, `section_count` 반영

---

## Step 3. 각 소스별 이미지 분할을 연결한다

### 목표
- 크롤링 후 모든 상세 이미지를 `sections/`로 통일 저장

### 해야 할 일
- `image_splitter.py`를 소스별로 실행
- 결과 섹션 번호를 소스 단위로 고유 식별 가능하게 관리

### 구현 포인트
- 내부 파일명은 단순 `section_001.png`여도 되지만
- 분석 단계에서는 `A_001`, `B_003` 같은 식별자가 필요

### TODO
- [ ] `detail_images -> sections` 변환 루프 작성
- [ ] 각 소스별 섹션 개수 계산
- [ ] `config.json`에 `section_count` 저장

### 완료 기준
- 모든 소스에 `sections/section_001.png` 형태의 파일 생성

---

## Step 4. 전체 섹션 인덱스를 만든다

### 목표
- 이후 AI 분석, 선택, 배열에 사용할 공통 메타데이터 테이블 생성

### 해야 할 일
- 각 섹션의 식별자, 소스, 경로를 모아 인덱스 파일 생성

### 권장 파일
- `analysis/section_index.json`

### 권장 필드
```json
{
  "sections": [
    {
      "id": "A_001",
      "source": "A",
      "role": "뼈대",
      "file": "A_naver_xxx/sections/section_001.png"
    }
  ]
}
```

### TODO
- [ ] 섹션 식별자 생성 규칙 확정
- [ ] 전체 섹션 인덱스 JSON 생성
- [ ] 이후 단계에서 이 파일만 참조하도록 통일

### 완료 기준
- 전체 멀티 작업 섹션이 하나의 JSON으로 조회 가능
- 이후 배치 분할 기준으로 재사용 가능

---

## Step 5. Phase 2용 섹션 역할 태깅 파이프라인을 만든다

### 목표
- 모든 섹션에 `role`, `copy_score`, `design_score`를 부여

### 해야 할 일
- 기존 단일 섹션 분석 프롬프트를 멀티 작업에 맞게 확장
- 결과를 JSON으로 누적 저장

### 구현 포인트
- 처음부터 완전 자동화하지 않아도 됨
- 1차는 수동/반자동으로라도 결과 스키마를 먼저 고정하는 게 중요

### 권장 출력 파일
- `analysis/section_analysis.json`

### TODO
- [ ] 역할 태그 목록 상수화
- [ ] 섹션 분석 결과 JSON 스키마 정의
- [ ] 분석 누적 저장 방식 결정
- [ ] 실패 섹션 재시도 방식 정의

### 완료 기준
- 전체 섹션에 대해 역할 태깅 결과 JSON 생성 가능

---

## Step 6. 역할별 베스트 섹션 선택 로직을 만든다

### 목표
- `section_analysis.json`을 바탕으로 역할별 선택 자동화

### 해야 할 일
- 같은 역할끼리 그룹핑
- 카피 베스트, 디자인 베스트 선택
- `FILLER` 제외

### 권장 출력 파일
- `analysis/best_selection.json`

### TODO
- [ ] 역할별 그룹핑 함수 작성
- [ ] copy/design 점수 기준 선택 로직 작성
- [ ] 동점 처리 규칙 정리
- [ ] 선택 이유 문자열 생성 규칙 작성

### 완료 기준
- 역할별 선택 결과가 JSON으로 자동 생성

---

## Step 7. 선택 결과 리뷰 HTML을 만든다

### 목표
- 사용자가 역할별 선택 결과를 바로 검토할 수 있게 한다
- 단, 실제 생성은 여기서 바로 하지 않고 5개 배치 계획으로 넘긴다

### 보여줄 것
- 역할명
- 카피 출처
- 디자인 출처
- 점수
- 썸네일
- 선택 이유

### 권장 출력 파일
- `review/selection_review.html`

### TODO
- [ ] 리뷰 HTML 템플릿 작성
- [ ] 썸네일 경로 매핑 처리
- [ ] 역할별 카드 UI 구성

### 완료 기준
- 사용자가 브라우저에서 선택 결과를 한눈에 볼 수 있음

---

## Step 8. CRO 기반 배열 로직을 만든다

### 목표
- 선택된 역할들을 최적 순서로 정렬

### 해야 할 일
- 기본 역할 순서 템플릿 정의
- 없는 역할은 스킵
- 중복 역할은 점수 순 또는 뼈대 우선 규칙 적용

### 권장 출력 파일
- `analysis/arrangement.json`

### TODO
- [ ] CRO 기본 순서 상수화
- [ ] 선택 결과와 순서 템플릿 매핑
- [ ] 배열 이유 생성
- [ ] 예외 규칙 정의

### 완료 기준
- 자동 배열 JSON 생성 가능

---

## Step 8-1. 배열 결과를 5개 배치 계획으로 분할한다

### 목표
- `arrangement.json`을 실제 작업 가능한 5개 단위 배치로 나눈다

### 이유
- 멀티 조합에서 품질을 가장 안정적으로 유지하는 방식이 5개 배치
- 선택과 배열이 맞더라도 한 번에 많이 생성하면 결과가 흔들릴 수 있음

### 권장 출력 파일
- `analysis/batch_plan.json`
- `review/batch_plan.md`

### TODO
- [ ] 기본 배치 크기 5 상수화
- [ ] 배열 결과를 5개 단위로 자르는 로직 작성
- [ ] 이미 완료된 compare 파일 기준 진행률 반영
- [ ] 다음 작업 배치 계산

### 완료 기준
- `1~5`, `6~10` 형태의 배치 계획이 자동 생성
- 다음 작업할 배치를 바로 확인 가능

---

## Step 9. 배열 리뷰 HTML을 만든다

### 목표
- 사용자가 실제 흐름을 미리 보며 순서를 검토할 수 있게 한다

### 보여줄 것
- 순서 번호
- 역할 태그
- 카피 출처
- 디자인 출처
- 썸네일

### 권장 출력 파일
- `review/arrangement_review.html`
- `review/batch_plan.md`

### TODO
- [ ] 배열 결과용 HTML 템플릿 작성
- [ ] 썸네일 리스트 UI 구성
- [ ] 추후 수동 순서 변경 가능성 고려
- [ ] 배치 경계가 보이도록 시각적으로 구분

### 완료 기준
- 사용자가 최종 섹션 흐름을 시각적으로 검토 가능

---

## Step 10. compare 생성 흐름을 멀티 소스 기준으로 확장한다

### 목표
- 최종 선택/배열 결과를 기준으로 compare HTML 생성

### 해야 할 일
- 기존 `compare_batch_manager.py` 구조 재활용
- 다만 파일 기준이 `detail_001` 순서가 아니라
- `arrangement.json` 기준 순서가 되도록 조정
- 실제 생성은 항상 현재 배치 5개만 대상으로 진행

### 구현 포인트
- 기존 단일용 스크립트를 바로 깨지 말고
- 멀티용 별도 스크립트 권장
  - 예: `src/multi_compare_batch_manager.py`

### TODO
- [ ] 멀티 배열 기준 배치 분할 로직 작성
- [ ] compare 파일명 규칙 정의
- [ ] 누적 `combined_review.html` 생성 방식 연결
- [ ] 배치 완료 후 다음 배치로 넘어가는 resume 규칙 추가

### 완료 기준
- 멀티 배열 기준으로 5개 단위 검토 가능
- 배치별 compare 생성 후 combined review 누적 갱신 가능

---

## Step 11. 카피 변형 단계는 마지막에 붙인다

### 목표
- 구조와 리뷰 흐름이 먼저 안정된 뒤 카피 생성 연결

### 이유
- 지금 가장 먼저 필요한 것은 "선택과 배열이 맞는가" 확인하는 것
- 카피까지 같이 붙이면 디버깅 지점이 너무 많아짐

### TODO
- [ ] `copy_variants.json` 스키마 정의
- [ ] 역할별 카피 프롬프트 템플릿 정리
- [ ] 원문/신규 카피 매핑 구조 정리

### 완료 기준
- 배열 확정 후 역할별 카피 변형 결과 생성 가능

---

## Step 12. 최종 HTML 통합은 제일 마지막에 한다

### 목표
- 전체 파이프라인이 안정된 뒤 최종 산출물 생성

### TODO
- [ ] `final_page.html` 생성 규칙 정의
- [ ] 섹션 연결 방식 통일
- [ ] 텍스트 분리 JSON 구조 정의

### 완료 기준
- compare 없이 결과물만 보는 최종 HTML 생성 가능

---

## 4. 우선순위 정리

## 1차 우선 구현
- [ ] `multi_job_manager.py` 생성
- [ ] 멀티 `config.json` 생성
- [ ] 멀티 크롤링 루프 연결
- [ ] 소스별 이미지 분할 연결
- [ ] `section_index.json` 생성

## 2차 우선 구현
- [ ] `section_analysis.json` 스키마 및 저장 방식 확정
- [ ] 역할별 베스트 선택 로직 구현
- [ ] `selection_review.html` 생성
- [ ] `arrangement.json` 생성
- [ ] `batch_plan.json` 생성
- [ ] `arrangement_review.html` 생성

## 3차 우선 구현
- [ ] 멀티 compare 배치 매니저 추가
- [ ] 멀티 combined review 생성
- [ ] `copy_variants.json` 연결

## 4차 우선 구현
- [ ] 최종 HTML 통합
- [ ] 제품 사진 교체 흐름 연결
- [ ] 텍스트 분리 출력

---

## 5. 실제 작업 순서 추천

가장 현실적인 작업 순서는 아래와 같다.

1. `multi_job_manager.py`부터 만든다.
2. 멀티 작업 폴더와 `config.json`이 정상 생성되는지 본다.
3. 크롤링과 분할을 멀티 작업으로 연결한다.
4. 전체 섹션 인덱스를 만든다.
5. 역할 태깅 결과를 저장하는 JSON 틀부터 고정한다.
6. 역할별 선택 로직을 붙인다.
7. 선택 리뷰 HTML을 만든다.
8. 배열 로직과 배열 리뷰 HTML을 만든다.
9. 배열 결과를 5개 배치 계획으로 자른다.
10. 그 다음에야 compare 배치와 최종 HTML로 들어간다.

즉, 지금은 "생성"보다 먼저 "선택과 배열" 단계를 구현하고,
생성 단계에서는 반드시 `5개 배치`를 유지하는 것이 맞다.

---

## 6. 파일 추가 제안

### 새로 만들 파일
- `src/multi_job_manager.py`
- `src/multi_compare_batch_manager.py`
- `docs/멀티_상세페이지_구현순서_TODO.md`

### 추후 필요할 수 있는 파일
- `src/multi_section_selector.py`
- `src/multi_arrangement_builder.py`
- `src/multi_review_renderer.py`

---

## 7. 작업 시 주의점

- 기존 단일용 스크립트는 바로 수정하지 말고 멀티용 진입점부터 분리
- 파일명, 폴더명, JSON 스키마를 먼저 고정하고 구현 시작
- 분석/선택/배열 단계는 결과 JSON을 남겨야 디버깅이 쉬움
- 사용자가 확인해야 하는 단계는 HTML 리뷰 파일로 반드시 분리
- 카피 변형과 최종 생성은 뒤로 미루고, 먼저 구조가 맞는지 검증
- 한 번에 전체를 만들지 말고 항상 배치 단위로 누적 검토

---

## 8. 최종 정리

현재 기준에서 가장 먼저 구현할 것은 `멀티 작업 관리자`입니다.

이유:
- 멀티 URL을 하나의 작업 단위로 묶어야 이후 단계가 연결됨
- 기존 `crawler.py`, `image_splitter.py`는 이미 충분히 재사용 가능
- 진짜 새로 필요한 것은 `전체 섹션을 모아서 선택하고 배열하는 관리층`이기 때문

따라서 다음 실제 개발 시작점은 아래 3개입니다.

- [ ] `multi_job_manager.py` 생성
- [ ] 멀티 작업용 `config.json` 생성
- [ ] 멀티 크롤링 + 분할 자동 연결
