# Seedream 이미지 분석 저장 구조

이 문서는 레이아웃 복원 분석과 별도로, 이미지 생성용 시각 분석을 저장하는 구조를 정의합니다.

## 왜 별도 저장이 필요한가

레이아웃 복원 분석은 HTML 재현용입니다.
하지만 이미지 생성 단계에서는 다른 정보가 필요합니다.

예:
- 제품 중심인지
- 인물 중심인지
- 전체 장면 중심인지
- 카메라 각도
- 배경 질감
- 조명 방향과 하이라이트
- 색조와 분위기
- 후처리 특징
- 최종 생성 프롬프트 EN/KR

즉 아래 두 데이터는 분리해야 합니다.

1. `layout spec`
- 위치, 크기, 폰트, 박스, 이미지 좌표
- 목적: HTML/CSS 재현

2. `seedream visual analysis`
- 이미지 생성용 장면 분석과 EN/KR 프롬프트
- 목적: Seedream 등 이미지 생성 모델 입력

## 저장 파일

- [seedream_master_prompt.txt](D:\Google Drive\코딩_VSCODE\Detail page maker\templates\seedream_master_prompt.txt)
- [seedream_prompt_result_schema.json](D:\Google Drive\코딩_VSCODE\Detail page maker\templates\seedream_prompt_result_schema.json)

## 권장 저장 방식

섹션마다 아래 3종을 저장합니다.

- `A_004_layout_spec.json`
- `A_004_text_assets.json`
- `A_004_seedream_analysis.json`

즉 한 섹션 기준으로:
- 복원용 레이아웃 데이터
- 텍스트 변형용 데이터
- 이미지 생성용 시각 분석 데이터

이 3개를 모두 보관합니다.

## seedream_analysis.json에 들어가야 할 것

### 1. focus_branch
- `OBJECT`
- `PERSON`
- `WHOLE_IMAGE`

### 2. image_ratio
- width
- height
- ratio_text

### 3. analysis
- `type_label`
- `camera_angle`
- `main_subject`
- `background`
- `composition`
- `lighting`
- `mood`
- `post_processing`
- `visible_interaction`
- `color_notes`
- `wardrobe_or_hand_notes`

### 4. prompts
- `english`
- `korean`

## 실제 운용 방식

### Step 1. 섹션 이미지 입력
사용자가 focus 선택:
- Product
- Person
- Whole image

### Step 2. AI 분석
`seedream_master_prompt.txt` 기준으로 분석하고
`seedream_prompt_result_schema.json` 형식으로 저장

### Step 3. 나중에 생성에 사용
- EN prompt 그대로 Seedream에 입력
- KR prompt는 검수용 또는 다른 모델용으로 사용
- ratio도 같이 유지

## 중요한 원칙

- 저장은 영어 중심이 맞습니다.
- 이유는 생성 모델 입력 원문이 보통 영어가 더 안정적이기 때문입니다.
- 다만 검수 편의 때문에 KR prompt도 같이 저장합니다.
- 분석 설명도 가능하면 영어 중심으로 쓰고, 내부 운영 메모만 한국어로 두는 편이 좋습니다.

## 결과적으로 섹션별 저장 구조는 이렇게 갑니다

예:
- `A_004_layout_spec.json`
- `A_004_text_assets.json`
- `A_004_seedream_analysis.json`

이렇게 하면:
- 재현은 layout spec으로
- 문구 변형은 text assets로
- 이미지 재생성은 seedream analysis로
분리해서 처리할 수 있습니다.
