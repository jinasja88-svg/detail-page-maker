# 섹션 복원용 레이아웃 분석 API 설계

이 문서는 나중에 OpenAI API로 섹션 재현 분석을 붙일 때 바로 쓸 수 있도록 정리한 기준 문서입니다.

## 목표

기존 역할 분류용 분석으로는 재현이 안 됩니다.
필요한 것은 다음입니다.

- 문자 내용
- 문자 위치
- 문자 크기
- 줄 수
- 글자수
- 글씨체 추정값
- 이미지 위치
- 이미지가 글씨 없는 순수 비주얼인지 여부
- 카드, 배경, pill, 그림자 같은 배치 요소

즉 API는 `무슨 섹션인지`보다 `어떻게 그려야 하는지`를 JSON으로 반환해야 합니다.

## 권장 API 구조

OpenAI 공식 문서 기준으로는 다음 조합이 맞습니다.

- 엔드포인트: `Responses API`
- 입력: `input_text` + `input_image`
- 출력: `Structured Outputs`의 `json_schema`
- 모델: `gpt-5.2` 우선
  - 비용/속도 절약형 대안은 `GPT-5 mini`

이유:
- Responses API는 이미지 입력을 받을 수 있습니다.
- Structured Outputs는 JSON schema에 맞는 출력을 강제할 수 있습니다.
- 나중에 renderer는 JSON만 읽으면 되므로 결과 편차를 줄일 수 있습니다.

## 요청 설계 원칙

### 1. 섹션 1장씩 분석
한 번에 여러 장을 넣으면 좌표 해석이 흔들릴 수 있습니다.
재현 단계에서는 섹션 1장씩 분석하는 것이 맞습니다.

### 2. 텍스트 없는 곳엔 text_block 생성 금지
이 규칙이 중요합니다.
기존 문제는 글자 없는 비주얼 섹션에도 텍스트를 억지로 넣은 것입니다.
프롬프트에서 명시적으로 금지해야 합니다.

### 3. 줄 수와 글자수 기록 필수
나중에 카피를 바꿀 때도 배치가 유지되려면 원문 길이 기준이 필요합니다.
그래서 각 텍스트 블록마다 아래를 반드시 받습니다.
- `estimated_line_count`
- `estimated_char_count`

### 4. 글씨 포함 이미지와 순수 이미지 구분
`image_blocks.has_embedded_text`가 중요합니다.
이게 있어야:
- 글씨 박힌 이미지는 통째로 쓰지 말지
- 제품만 크롭할지
- 배경만 사용할지
를 판단할 수 있습니다.

## 출력 스키마

파일:
- [layout_reconstruction_schema.json](D:\Google Drive\코딩_VSCODE\Detail page maker\templates\layout_reconstruction_schema.json)

핵심 구조:
- `canvas`
- `background`
- `text_blocks`
- `image_blocks`
- `shape_blocks`
- `inference_notes`

### text_blocks
각 텍스트 블록에는 최소한 아래가 있어야 합니다.
- `text`
- `x, y, w, h`
- `font_size`
- `font_weight`
- `line_height`
- `letter_spacing`
- `align`
- `color`
- `estimated_line_count`
- `estimated_char_count`
- `font_family_guess`
- `font_family_css`

### image_blocks
각 이미지 블록에는 최소한 아래가 있어야 합니다.
- `kind`
- `x, y, w, h`
- `fit`
- `source_hint`
- `has_embedded_text`

### shape_blocks
레이아웃 감을 좌우하는 도형입니다.
- 카드
- pill
- divider
- shadow
- mask
- gradient blob

이 데이터를 빼면 원본 느낌이 무너집니다.

## 실제 요청 예시

```json
{
  "model": "gpt-5.2",
  "input": [
    {
      "role": "system",
      "content": [
        {
          "type": "input_text",
          "text": "You are extracting reconstruction-ready layout data from a Korean e-commerce detail-page section. Return only JSON that matches the schema."
        }
      ]
    },
    {
      "role": "user",
      "content": [
        {
          "type": "input_text",
          "text": "Analyze this section for layout reconstruction. Do not invent text blocks in image-only areas."
        },
        {
          "type": "input_image",
          "image_url": "https://.../section_004.png"
        }
      ]
    }
  ],
  "text": {
    "format": {
      "type": "json_schema",
      "name": "layout_reconstruction",
      "strict": true,
      "schema": {}
    }
  }
}
```

실제 구현 시 `schema` 자리에 `layout_reconstruction_schema.json` 내용을 넣습니다.

## 렌더러 연결 방식

이 API는 분석기입니다.
실제 재현은 코드가 합니다.

흐름:
1. 섹션 이미지 1장 입력
2. API가 `layout_spec.json` 반환
3. renderer가 `text_blocks`, `image_blocks`, `shape_blocks`를 읽음
4. 절대 좌표 HTML/CSS 생성
5. compare에서 원본과 대조

즉 앞으로는 `PRODUCT_INTRO 템플릿`으로 그리는 게 아니라,
`A_004의 layout_spec`으로 그려야 합니다.

## 구현 우선순위

1. `A_004` 같은 1개 섹션에 대해 API 분석 결과 저장
2. 그 JSON으로 `detailed.html` 생성
3. compare 확인
4. 맞으면 2, 3, 4, 7, 8, 11 섹션으로 확장

## OpenAI 공식 문서 기준

공식 문서에서 확인한 기준:
- Responses API는 이미지 입력과 구조화된 출력을 지원합니다.
- Structured Outputs는 JSON schema 준수를 보장하는 방향으로 쓰는 것이 권장됩니다.
- 이미지 입력은 Responses API에서 처리할 수 있습니다.
- 최신 모델 목록에는 `gpt-5.2`, `GPT-5 mini`, `GPT-5 nano`가 있습니다.

출처:
- https://platform.openai.com/docs/api-reference/responses/retrieve
- https://platform.openai.com/docs/guides/structured-outputs?lang=javascript
- https://platform.openai.com/docs/guides/images-vision
- https://platform.openai.com/docs/models

## 결론

나중에 API로 붙일 때는 다음이 기준입니다.
- 역할 분석 X
- 레이아웃 복원 분석 O
- 1장씩 분석
- strict json_schema 사용
- 텍스트 없는 영역엔 text_block 생성 금지
- 글자수/줄수 데이터 필수
- 이미지 블록은 텍스트 포함 여부까지 기록
