"""
캡차를 파일 기반으로 처리하는 테스트 스크립트.
1. 캡차 발생 → output/_captcha_temp.png 저장 + output/_captcha_waiting 생성
2. 외부에서 답을 output/_captcha_answer.txt에 기록
3. 스크립트가 답을 읽고 제출
"""
import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(__file__))
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from crawler import DetailPageCrawler

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
CAPTCHA_IMG = os.path.join(OUTPUT_DIR, "_captcha_temp.png")
CAPTCHA_WAITING = os.path.join(OUTPUT_DIR, "_captcha_waiting")
CAPTCHA_ANSWER = os.path.join(OUTPUT_DIR, "_captcha_answer.txt")


async def file_captcha_handler(screenshot_b64: str, platform: str) -> str:
    """캡차 스크린샷을 파일로 저장하고, 답 파일이 생길 때까지 대기한다."""
    import base64

    # 스크린샷 저장
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(CAPTCHA_IMG, "wb") as f:
        f.write(base64.b64decode(screenshot_b64))

    # 답 파일 초기화
    if os.path.exists(CAPTCHA_ANSWER):
        os.remove(CAPTCHA_ANSWER)

    # 대기 신호 파일 생성
    with open(CAPTCHA_WAITING, "w") as f:
        f.write(platform)

    print(f"   [캡차 대기중] 이미지: {CAPTCHA_IMG}")
    print(f"   [캡차 대기중] 답을 {CAPTCHA_ANSWER} 에 써주세요")

    # 답 파일이 생길 때까지 대기 (최대 120초)
    for _ in range(240):
        if os.path.exists(CAPTCHA_ANSWER):
            with open(CAPTCHA_ANSWER, "r", encoding="utf-8") as f:
                answer = f.read().strip()
            # 정리
            os.remove(CAPTCHA_ANSWER)
            if os.path.exists(CAPTCHA_WAITING):
                os.remove(CAPTCHA_WAITING)
            print(f"   [캡차] 답 수신: {answer}")
            return answer
        await asyncio.sleep(0.5)

    print("   [캡차] 시간 초과")
    if os.path.exists(CAPTCHA_WAITING):
        os.remove(CAPTCHA_WAITING)
    return ""


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://smartstore.naver.com/iotlink/products/11606430313"

    crawler = DetailPageCrawler(
        output_dir=OUTPUT_DIR,
        on_captcha=file_captcha_handler,
    )
    result = await crawler.crawl(url)
    print("\n=== 결과 ===")
    print(f"상세 이미지: {result.get('detail_image_count', 0)}개")
    print(f"메인 이미지: {result.get('main_image_count', 0)}개")


if __name__ == "__main__":
    asyncio.run(main())
