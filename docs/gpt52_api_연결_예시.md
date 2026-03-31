# GPT-5.2 API 연결 예시

> 목적:
> 현재 멀티 상세페이지 파이프라인에서 나중에 OpenAI API를 붙일 때
> 결과 편차를 줄이기 위해 `모델`, `프롬프트`, `JSON schema`, `배치 규칙`을 먼저 고정한다.

---

## 1. 추천 모델

### 섹션 분석 / 역할 태깅 / 카피 변형
- `gpt-5.2`

### 코딩/에이전트형 개발 작업
- `gpt-5.2-codex`

이 프로젝트에서 실제 상품 상세페이지 분석용 기본 모델은 `gpt-5.2`로 잡는다.

---

## 2. 왜 이렇게 잡는가

- 지금 Codex에서 코드/파이프라인을 만들고 있음
- 나중에 API에서는 섹션 분석, 카피 변형, 이미지 입력 기반 판단을 수행할 예정
- 이때 가장 중요한 것은 "같은 모델명"보다 `같은 입력 구조 + 같은 출력 스키마 + 같은 배치 규칙`이다

즉:

- 모델: `gpt-5.2`
- 인터페이스: `Responses API`
- 출력: `Structured Outputs(JSON Schema)`
- 처리 단위: `5개 배치`

이 4개를 고정해야 결과가 흔들리지 않는다.

---

## 3. 섹션 분석 API 예시

### 입력 목적
- 이미지 1장 또는 5장 이하 묶음을 넣고
- 각 섹션의 역할, 카피 텍스트, 점수를 구조화해서 받는다

### 권장 방식
- 한 요청에 최대 `5개 섹션`
- 이미지 순서를 그대로 유지
- 응답은 JSON Schema 강제

### 예시 요청 바디

```json
{
  "model": "gpt-5.2",
  "reasoning": {
    "effort": "low"
  },
  "input": [
    {
      "role": "system",
      "content": [
        {
          "type": "input_text",
          "text": "You are analyzing Korean e-commerce detail page sections. Return only JSON matching the schema."
        }
      ]
    },
    {
      "role": "user",
      "content": [
        {
          "type": "input_text",
          "text": "다음 섹션 이미지들을 순서대로 분석해 role, copy_text, copy_score, design_score, core_message를 JSON으로 반환해줘."
        },
        {
          "type": "input_image",
          "image_url": "https://example.com/section_001.png"
        },
        {
          "type": "input_image",
          "image_url": "https://example.com/section_002.png"
        }
      ]
    }
  ],
  "text": {
    "format": {
      "type": "json_schema",
      "name": "section_analysis_batch",
      "schema": {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "additionalProperties": false,
        "required": ["sections"],
        "properties": {
          "sections": {
            "type": "array",
            "items": {
              "type": "object",
              "additionalProperties": false,
              "required": [
                "input_index",
                "role",
                "copy_text",
                "copy_score",
                "design_score",
                "core_message"
              ],
              "properties": {
                "input_index": {
                  "type": "integer"
                },
                "role": {
                  "type": "string",
                  "enum": [
                    "HOOK",
                    "PAIN",
                    "SOLUTION",
                    "FEATURE",
                    "BENEFIT",
                    "SOCIAL_PROOF",
                    "HOW_TO",
                    "COMPARE",
                    "INGREDIENT",
                    "BRAND",
                    "GUARANTEE",
                    "BUNDLE",
                    "CTA",
                    "FILLER"
                  ]
                },
                "copy_text": {
                  "type": "string"
                },
                "copy_score": {
                  "type": "integer",
                  "minimum": 1,
                  "maximum": 10
                },
                "design_score": {
                  "type": "integer",
                  "minimum": 1,
                  "maximum": 10
                },
                "core_message": {
                  "type": "string"
                }
              }
            }
          }
        }
      }
    }
  }
}
```

---

## 4. 카피 변형 API 예시

### 목적
- 경쟁사 카피를 그대로 쓰지 않고
- 핵심 메시지만 유지한 새 카피를 생성

### 예시 요청 바디

```json
{
  "model": "gpt-5.2",
  "reasoning": {
    "effort": "low"
  },
  "input": [
    {
      "role": "system",
      "content": [
        {
          "type": "input_text",
          "text": "You rewrite Korean marketing copy for detail pages. Return only JSON matching the schema. Do not preserve 3 or more consecutive eojeol from the source."
        }
      ]
    },
    {
      "role": "user",
      "content": [
        {
          "type": "input_text",
          "text": "원본 카피를 내 상품 기준으로 재작성해줘.\n상품명: 메수스 진동 핸디 마사지건\n특징: 휘어진 구조, 12단 조절, 12시간 배터리\n타겟: 컴퓨터 작업 많은 사람, 노인\n원본 카피: 손이 닿지 않는 곳까지 시원하게\n역할: BENEFIT"
        }
      ]
    }
  ],
  "text": {
    "format": {
      "type": "json_schema",
      "name": "copy_variant",
      "schema": {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "additionalProperties": false,
        "required": ["role", "new_copy", "persuasion_structure"],
        "properties": {
          "role": {
            "type": "string"
          },
          "new_copy": {
            "type": "string"
          },
          "persuasion_structure": {
            "type": "string"
          }
        }
      }
    }
  }
}
```

---

## 5. 결과 차이를 줄이기 위한 고정 규칙

### 반드시 고정할 것
- 모델명: `gpt-5.2`
- API: `Responses API`
- 출력: `Structured Outputs`
- reasoning.effort: `low`부터 시작
- 입력 이미지 순서
- 5개 배치 단위

### 코드에서 고정할 것
- 역할 목록 enum
- 점수 범위 1~10
- 선택 기준: copy_score, design_score
- 배열 기준: CRO 순서
- 배치 분할 기준: 5개

### AI에 맡기지 말 것
- 역할 순서 최종 확정
- 배치 나누기
- 완료 여부 판정
- 파일명 규칙

---

## 6. 실제 운영 순서

1. `multi_job_manager.py`로 수집/분할
2. `gpt-5.2`로 `section_analysis.json` 생성
3. `multi_section_selector.py`로 `best_selection.json` 생성
4. `multi_arrangement_builder.py`로 `arrangement.json` 생성
5. `multi_compare_batch_manager.py`로 5개 배치 compare 생성

즉, AI는 분석과 재작성에만 쓰고
선택/배열/배치의 최종 결정은 최대한 코드 규칙으로 고정한다.

---

## 7. 이 문서를 쓰는 이유

지금 Codex에서 테스트한 흐름과
나중에 API로 붙였을 때의 차이를 줄이려면,
프롬프트 문장보다도 `입력 구조`와 `응답 스키마`를 먼저 고정하는 것이 더 중요하다.

이 문서는 그 기준선이다.
