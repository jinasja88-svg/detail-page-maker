"""
상세페이지 크롤러 - 쿠팡/네이버/카페24
- 브라우저로 페이지 로딩 → 캡차 감지 → 사용자 입력 → 이미지 추출
"""

import os
import sys
import re
import json
import hashlib
import asyncio
import base64
from urllib.parse import urljoin, urlparse

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from bs4 import BeautifulSoup
import requests


def detect_platform(url: str) -> str:
    domain = urlparse(url).netloc.lower()
    if "coupang.com" in domain:
        return "coupang"
    if "naver.com" in domain:
        return "naver"
    if "cafe24" in domain:
        return "cafe24"
    return "unknown"


# =============================================================================
# 캡차 처리
# =============================================================================

class CaptchaHandler:
    """
    캡차 감지 및 사용자 입력 처리.
    - CLI 모드: 터미널에서 직접 입력
    - 웹 모드: 콜백 함수로 스크린샷 전달 → 답변 수신
    """

    # 각 플랫폼별 캡차 감지 패턴
    CAPTCHA_INDICATORS = {
        "naver": ["보안 확인", "정답을 입력", "빈 칸을 채워"],
        "coupang": ["Access Denied", "You don't have permission"],
    }

    def __init__(self, on_captcha=None):
        """
        Args:
            on_captcha: 캡차 발생 시 호출되는 콜백 함수.
                        signature: async def on_captcha(screenshot_base64: str, platform: str) -> str
                        반환값: 사용자가 입력한 캡차 답
                        None이면 CLI 모드 (터미널 input)
        """
        self.on_captcha = on_captcha

    async def detect_and_solve(self, page, platform: str) -> bool:
        """
        캡차가 있으면 감지하고 사용자에게 풀도록 요청한다.
        Returns: True면 캡차를 풀었음, False면 캡차 없었음
        """
        html = await page.content()
        indicators = self.CAPTCHA_INDICATORS.get(platform, [])

        has_captcha = any(ind in html for ind in indicators)
        if not has_captcha:
            return False

        print("   [!] 캡차 감지됨 - 사용자 입력 필요")

        # 최대 3번 시도
        for attempt in range(3):
            # 스크린샷 촬영
            screenshot_bytes = await page.screenshot()
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode()

            # 사용자에게 캡차 답 요청
            if self.on_captcha:
                # 웹 모드: 콜백으로 스크린샷 전달
                answer = await self.on_captcha(screenshot_b64, platform)
            else:
                # CLI 모드: 터미널에서 입력
                # 스크린샷을 임시 파일로 저장해서 보여줌
                temp_path = os.path.join(os.path.dirname(__file__), "..", "output", "_captcha_temp.png")
                os.makedirs(os.path.dirname(temp_path), exist_ok=True)
                with open(temp_path, "wb") as f:
                    f.write(screenshot_bytes)
                print(f"   캡차 이미지 저장: {os.path.abspath(temp_path)}")
                print(f"   이미지를 확인하고 답을 입력해주세요.")
                answer = input("   캡차 답: ").strip()

            if not answer:
                print("   답이 비어있습니다. 건너뜁니다.")
                return False

            # 캡차 입력
            solved = await self._submit_captcha(page, platform, answer)
            if solved:
                print("   [OK] 캡차 통과!")
                return True
            else:
                print(f"   캡차 실패 (시도 {attempt + 1}/3)")

        print("   캡차 3회 실패")
        return False

    async def _submit_captcha(self, page, platform: str, answer: str) -> bool:
        """캡차 답을 입력하고 제출한다."""
        try:
            if platform == "naver":
                # 네이버: 입력 필드에 답 입력 → 확인 버튼 클릭
                input_el = await page.query_selector("input[placeholder*='입력'], input[type='text']")
                if input_el:
                    await input_el.fill(answer)
                    # 확인 버튼 클릭
                    submit_btn = await page.query_selector("button:has-text('확인'), input[type='submit']")
                    if submit_btn:
                        await submit_btn.click()
                    else:
                        await input_el.press("Enter")
                    await asyncio.sleep(3)

            elif platform == "coupang":
                # 쿠팡: Access Denied는 캡차가 아니라 IP 차단
                # 페이지 새로고침으로 재시도
                await page.reload(wait_until="domcontentloaded")
                await asyncio.sleep(3)

            # 캡차가 풀렸는지 확인
            html = await page.content()
            indicators = self.CAPTCHA_INDICATORS.get(platform, [])
            still_captcha = any(ind in html for ind in indicators)
            return not still_captcha

        except Exception as e:
            print(f"   캡차 제출 에러: {e}")
            return False


# =============================================================================
# 플랫폼별 이미지 추출
# =============================================================================

class CoupangExtractor:
    DETAIL_SELECTORS = [
        ".product-detail-content-inside",
        ".prod-description",
        "#productDetail",
    ]

    async def extract(self, page, url: str) -> dict:
        # 1. 더보기 버튼 클릭
        try:
            btn = await page.query_selector(
                ".prod-description__toggle-btn, .product-detail-toggle-btn, button[class*='toggle']"
            )
            if btn:
                await btn.click()
                print("   [쿠팡] '상세페이지 더보기' 클릭")
                await asyncio.sleep(2)
                # 더보기 클릭 후 스크롤 → lazy-load 이미지 로딩
                print("   [쿠팡] 상세 이미지 로딩 중 (스크롤)...")
                total = await page.evaluate("document.body.scrollHeight")
                pos = 0
                while pos < total:
                    pos += 600
                    await page.evaluate(f"window.scrollTo(0, {pos})")
                    await asyncio.sleep(0.3)
                    total = await page.evaluate("document.body.scrollHeight")
                await page.evaluate("window.scrollTo(0, 0)")
                await asyncio.sleep(1)
        except Exception:
            pass

        detail_html = ""
        for sel in self.DETAIL_SELECTORS:
            el = await page.query_selector(sel)
            if el:
                detail_html = await el.inner_html()
                if len(detail_html) > 100:
                    print(f"   [쿠팡] 상세영역: {sel}")
                    break

        if not detail_html:
            detail_html = await page.content()

        soup = BeautifulSoup(detail_html, "html.parser")
        detail_images = []
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
            if src:
                full = urljoin(url, src)
                if "coupangcdn.com" in full:
                    full = re.sub(r"/q\d+/", "/q100/", full)
                    detail_images.append(full)

        main_images = []
        for img in await page.query_selector_all(".prod-image__detail img, .prod-image__item img"):
            src = await img.get_attribute("src") or await img.get_attribute("data-src")
            if src:
                full = urljoin(url, src)
                full = re.sub(r"/q\d+/", "/q100/", full)
                main_images.append(full)

        return {"detail_html": detail_html, "detail_images": detail_images, "main_images": main_images}


class NaverExtractor:
    DETAIL_SELECTORS = [
        ".se-main-container",
        "._se_component_area",
        "#INTRODUCE",
        "div[class*='detail_cont']",
    ]

    async def extract(self, page, url: str) -> dict:
        # 1. 펼쳐보기 클릭
        try:
            for btn in await page.query_selector_all("a, button"):
                text = await btn.text_content() or ""
                if "펼쳐보기" in text or "더보기" in text:
                    if await btn.is_visible():
                        await btn.click()
                        print("   [네이버] '펼쳐보기' 클릭")
                        await asyncio.sleep(2)
                        break
        except Exception:
            pass

        # 2. 펼쳐진 후 스크롤 → lazy-load 이미지 전부 로딩
        print("   [네이버] 상세 이미지 로딩 중 (스크롤)...")
        await self._scroll_to_load(page)

        # 3. 상세 영역 HTML 추출
        detail_html = ""
        for sel in self.DETAIL_SELECTORS:
            el = await page.query_selector(sel)
            if el:
                detail_html = await el.inner_html()
                if len(detail_html) > 100:
                    print(f"   [네이버] 상세영역: {sel}")
                    break

        if not detail_html:
            detail_html = await page.content()

        # 4. HTML에서 이미지 추출
        soup = BeautifulSoup(detail_html, "html.parser")
        detail_images = []
        for img in soup.find_all("img"):
            src = img.get("src") or ""
            # src가 base64 플레이스홀더면 data-src 사용
            if src.startswith("data:"):
                src = img.get("data-src") or img.get("data-lazy-src") or ""
            elif not src:
                src = img.get("data-src") or img.get("data-lazy-src") or ""
            if src:
                full = urljoin(url, src)
                if full.startswith("http"):
                    full = re.sub(r"\?type=\w+", "", full)
                    detail_images.append(full)

        # 5. DOM에서도 직접 추출 (JS로 렌더된 이미지 포함)
        dom_images = await page.evaluate("""
            () => {
                const imgs = [];
                const selectors = [
                    '.se-main-container img',
                    '._se_component_area img',
                    '#INTRODUCE img',
                    'div[class*="detail"] img',
                ];
                for (const sel of selectors) {
                    document.querySelectorAll(sel).forEach(img => {
                        const src = img.src || img.dataset.src || img.dataset.lazySrc;
                        if (src && src.startsWith('http')) imgs.push(src);
                    });
                    if (imgs.length > 0) break;
                }
                return imgs;
            }
        """)
        # DOM에서 찾은 이미지 합치기 (중복 제거)
        seen = set(detail_images)
        for img_url in dom_images:
            clean = re.sub(r"\?type=\w+", "", img_url)
            if clean not in seen:
                detail_images.append(clean)
                seen.add(clean)

        # 메인 이미지
        main_images = []
        for img in await page.query_selector_all("img[alt*='상품'], ._2-I30XS1lA img, .bd_2dy3Y img"):
            src = await img.get_attribute("src") or await img.get_attribute("data-src")
            if src and src.startswith("http"):
                main_images.append(re.sub(r"\?type=\w+", "", src))

        return {"detail_html": detail_html, "detail_images": detail_images, "main_images": main_images}

    async def _scroll_to_load(self, page):
        """펼쳐진 상세 영역을 천천히 스크롤하여 lazy-load 이미지를 전부 로딩한다."""
        total = await page.evaluate("document.body.scrollHeight")
        pos = 0
        while pos < total:
            pos += 600
            await page.evaluate(f"window.scrollTo(0, {pos})")
            await asyncio.sleep(0.4)
            total = await page.evaluate("document.body.scrollHeight")
        # 맨 위로
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(1)


class Cafe24Extractor:
    DETAIL_SELECTORS = [
        "#prdDetail", ".detail_cont", ".xans-product-detail",
        "#goods_description", ".goods_description",
    ]

    async def extract(self, page, url: str) -> dict:
        detail_html = ""
        for sel in self.DETAIL_SELECTORS:
            el = await page.query_selector(sel)
            if el:
                detail_html = await el.inner_html()
                if len(detail_html) > 100:
                    print(f"   [카페24] 상세영역: {sel}")
                    break

        if not detail_html:
            detail_html = await page.content()

        soup = BeautifulSoup(detail_html, "html.parser")
        detail_images = []
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or img.get("ec-data-src")
            if src:
                full = urljoin(url, src)
                path = urlparse(full).path.lower()
                if any(path.endswith(e) for e in (".png", ".jpg", ".jpeg", ".gif", ".webp")):
                    detail_images.append(full)

        main_images = []
        for img in await page.query_selector_all(".xans-product-image img, #mainImage, .BigImage img"):
            src = await img.get_attribute("src") or await img.get_attribute("data-src")
            if src:
                main_images.append(urljoin(url, src))

        return {"detail_html": detail_html, "detail_images": detail_images, "main_images": main_images}


# =============================================================================
# 메인 크롤러
# =============================================================================

class DetailPageCrawler:
    def __init__(self, output_dir="output", proxy=None, on_captcha=None):
        """
        Args:
            output_dir: 결과 저장 디렉토리
            proxy: 프록시 URL (예: "http://user:pass@proxy:8080")
            on_captcha: 캡차 콜백 함수 (None이면 CLI 모드)
                        async def on_captcha(screenshot_b64: str, platform: str) -> str
        """
        self.output_dir = output_dir
        self.proxy = proxy
        self.captcha_handler = CaptchaHandler(on_captcha=on_captcha)
        self.extractors = {
            "coupang": CoupangExtractor(),
            "naver": NaverExtractor(),
            "cafe24": Cafe24Extractor(),
        }

    async def crawl(self, url: str) -> dict:
        """URL에서 상세페이지를 크롤링한다."""
        platform = detect_platform(url)
        print(f"[플랫폼] {platform}")

        # 출력 디렉토리
        project_name = self._make_project_name(url)
        project_dir = os.path.join(self.output_dir, project_name)
        images_dir = os.path.join(project_dir, "detail_images")
        main_images_dir = os.path.join(project_dir, "main_images")
        os.makedirs(images_dir, exist_ok=True)
        os.makedirs(main_images_dir, exist_ok=True)

        async with async_playwright() as p:
            # 브라우저 실행
            launch_args = {"headless": False, "channel": "chrome"}
            if self.proxy:
                launch_args["proxy"] = {"server": self.proxy}

            browser = await p.chromium.launch(**launch_args)
            context = await browser.new_context(viewport={"width": 1400, "height": 900})
            stealth = Stealth()
            await stealth.apply_stealth_async(context)
            page = await context.new_page()

            # 1. 페이지 로딩
            print("[1/4] 페이지 로딩...")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(3)

            # 2. 캡차 확인 및 처리
            print("[2/4] 캡차 확인...")
            captcha_solved = await self.captcha_handler.detect_and_solve(page, platform)
            if captcha_solved:
                await asyncio.sleep(2)

            # unknown이면 HTML로 재판별
            if platform == "unknown":
                html = await page.content()
                hl = html.lower()
                if "cafe24" in hl or "xans-product" in hl:
                    platform = "cafe24"
                elif "naver" in hl:
                    platform = "naver"

            # 3. 스크롤 (카페24/기타만 - 네이버/쿠팡은 extractor 내부에서 펼치기 후 스크롤)
            if platform not in ("naver", "coupang"):
                print("[3/4] 이미지 로딩 (스크롤)...")
                await self._scroll_page(page)
            else:
                print("[3/4] 스크롤은 추출 단계에서 처리")

            # 4. 이미지 추출
            print("[4/4] 이미지 추출...")
            extractor = self.extractors.get(platform)
            if extractor:
                data = await extractor.extract(page, url)
            else:
                data = await self._generic_extract(page, url)

            # 스크린샷
            screenshot_path = os.path.join(project_dir, "full_page.png")
            await page.screenshot(path=screenshot_path, full_page=True)

            await browser.close()

        # HTML 저장
        detail_html_path = os.path.join(project_dir, "detail_section.html")
        with open(detail_html_path, "w", encoding="utf-8") as f:
            f.write(data.get("detail_html", ""))

        # 이미지 다운로드
        detail_imgs = list(dict.fromkeys(data.get("detail_images", [])))  # 중복 제거
        main_imgs = list(dict.fromkeys(data.get("main_images", [])))

        print(f"   발견: 상세 {len(detail_imgs)}개, 메인 {len(main_imgs)}개")

        dl_detail = self._download_images(detail_imgs, images_dir, "detail")
        dl_main = self._download_images(main_imgs, main_images_dir, "main")

        result = {
            "url": url,
            "platform": platform,
            "project_dir": project_dir,
            "detail_html_path": detail_html_path,
            "screenshot_path": screenshot_path,
            "detail_images": dl_detail,
            "main_images": dl_main,
            "detail_image_count": len(dl_detail),
            "main_image_count": len(dl_main),
        }

        with open(os.path.join(project_dir, "crawl_result.json"), "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\n[완료] {platform} | 상세 {len(dl_detail)}개 | 메인 {len(dl_main)}개")
        print(f"   저장: {project_dir}")
        return result

    async def _scroll_page(self, page):
        total = await page.evaluate("document.body.scrollHeight")
        pos = 0
        while pos < total:
            pos += 900
            await page.evaluate(f"window.scrollTo(0, {pos})")
            await asyncio.sleep(0.3)
            total = await page.evaluate("document.body.scrollHeight")
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(0.5)

    async def _generic_extract(self, page, url: str) -> dict:
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")
        imgs = []
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src")
            if src:
                imgs.append(urljoin(url, src))
        return {"detail_html": html, "detail_images": imgs, "main_images": []}

    def _download_images(self, urls: list[str], save_dir: str, prefix: str) -> list[str]:
        downloaded = []
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        for i, url in enumerate(urls):
            try:
                ext = self._get_ext(url)
                fname = f"{prefix}_{i+1:03d}{ext}"
                path = os.path.join(save_dir, fname)

                resp = requests.get(url, headers=headers, timeout=15)
                if resp.status_code == 200 and len(resp.content) > 1000:
                    with open(path, "wb") as f:
                        f.write(resp.content)
                    downloaded.append(path)
                    print(f"   + {fname} ({len(resp.content)//1024}KB)")
            except Exception as e:
                print(f"   x 실패: {url[:50]}... ({e})")
        return downloaded

    def _get_ext(self, url: str) -> str:
        path = urlparse(url).path.lower()
        for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
            if ext in path:
                return ext
        return ".jpg"

    def _make_project_name(self, url: str) -> str:
        domain = urlparse(url).netloc.replace("www.", "")
        h = hashlib.md5(url.encode()).hexdigest()[:8]
        safe = re.sub(r"[^a-zA-Z0-9]", "_", domain)
        return f"{safe}_{h}"


# =============================================================================
# CLI 실행
# =============================================================================

async def main():
    if len(sys.argv) < 2:
        print("사용법: python crawler.py <URL> [프록시URL]")
        print("지원: 쿠팡, 네이버 스마트스토어, 카페24")
        sys.exit(1)

    url = sys.argv[1]
    proxy = sys.argv[2] if len(sys.argv) > 2 else None
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")

    crawler = DetailPageCrawler(output_dir=output_dir, proxy=proxy)
    await crawler.crawl(url)


if __name__ == "__main__":
    asyncio.run(main())
