/**
 * 상세페이지 이미지 추출 Content Script
 * 각 플랫폼별로 상세페이지 영역을 찾고 이미지 URL을 추출한다.
 */

(() => {
  // 플랫폼 감지
  function detectPlatform() {
    const host = location.hostname;
    if (host.includes("coupang.com")) return "coupang";
    if (host.includes("naver.com")) return "naver";
    // cafe24는 HTML로 판별
    const html = document.documentElement.innerHTML;
    if (html.includes("cafe24") || html.includes("xans-product") || html.includes("ec-data-src")) {
      return "cafe24";
    }
    return "unknown";
  }

  // ====== 쿠팡 ======
  function extractCoupang() {
    const result = { detail: [], main: [], expandNeeded: false };

    // 더보기 버튼 확인
    const toggleBtn = document.querySelector(
      ".prod-description__toggle-btn, .product-detail-toggle-btn, button[class*='toggle']"
    );
    if (toggleBtn) {
      toggleBtn.click();
      result.expandNeeded = true;
    }

    // 상세 영역 이미지
    const detailSelectors = [
      ".product-detail-content-inside",
      ".prod-description",
      "#productDetail",
    ];

    for (const sel of detailSelectors) {
      const el = document.querySelector(sel);
      if (el && el.innerHTML.length > 100) {
        const imgs = el.querySelectorAll("img");
        imgs.forEach((img) => {
          const src = img.src || img.dataset.src || img.dataset.lazySrc;
          if (src && src.includes("coupangcdn.com")) {
            // 고화질로 변환
            const hq = src.replace(/\/q\d+\//, "/q100/");
            result.detail.push(hq);
          }
        });
        break;
      }
    }

    // 메인 상품 이미지
    document.querySelectorAll(".prod-image__detail img, .prod-image__item img").forEach((img) => {
      const src = img.src || img.dataset.src;
      if (src) {
        const hq = src.replace(/\/q\d+\//, "/q100/");
        result.main.push(hq);
      }
    });

    return result;
  }

  // ====== 네이버 스마트스토어 ======
  function extractNaver() {
    const result = { detail: [], main: [], expandNeeded: false };

    // 펼쳐보기 버튼 클릭
    const expandBtns = document.querySelectorAll(
      "a[class*='more'], button[class*='more'], a[class*='unfold'], button[class*='unfold']"
    );
    for (const btn of expandBtns) {
      const text = btn.textContent || "";
      if (text.includes("펼쳐보기") || text.includes("더보기")) {
        btn.click();
        result.expandNeeded = true;
        break;
      }
    }

    // 상세 영역 이미지
    const detailSelectors = [
      ".se-main-container",
      "._se_component_area",
      "#INTRODUCE",
      "div[class*='detail_cont']",
    ];

    for (const sel of detailSelectors) {
      const el = document.querySelector(sel);
      if (el && el.innerHTML.length > 100) {
        el.querySelectorAll("img").forEach((img) => {
          const src = img.src || img.dataset.src || img.dataset.lazySrc;
          if (src && src.startsWith("http")) {
            // 고화질 원본으로 변환
            const hq = src.replace(/\?type=\w+/, "");
            result.detail.push(hq);
          }
        });
        break;
      }
    }

    // 메인 상품 이미지
    document.querySelectorAll("._2-I30XS1lA img, .bd_2dy3Y img, ._2QmvJFNzsa img").forEach((img) => {
      const src = img.src || img.dataset.src;
      if (src && src.startsWith("http")) {
        const hq = src.replace(/\?type=\w+/, "");
        result.main.push(hq);
      }
    });

    return result;
  }

  // ====== 카페24 ======
  function extractCafe24() {
    const result = { detail: [], main: [] };

    const detailSelectors = [
      "#prdDetail",
      ".detail_cont",
      ".xans-product-detail .cont",
      ".xans-product-detail",
      "#goods_description",
      ".goods_description",
    ];

    for (const sel of detailSelectors) {
      const el = document.querySelector(sel);
      if (el && el.innerHTML.length > 100) {
        el.querySelectorAll("img").forEach((img) => {
          const src = img.src || img.dataset.src || img.getAttribute("ec-data-src");
          if (src && src.startsWith("http")) {
            result.detail.push(src);
          }
        });
        break;
      }
    }

    // 메인 이미지
    document.querySelectorAll(".xans-product-image img, #mainImage, .BigImage img").forEach((img) => {
      const src = img.src || img.dataset.src;
      if (src) result.main.push(src);
    });

    return result;
  }

  // ====== 범용 추출 ======
  function extractGeneric() {
    const result = { detail: [], main: [] };
    // 페이지 내 모든 큰 이미지
    document.querySelectorAll("img").forEach((img) => {
      if (img.naturalWidth > 200 && img.naturalHeight > 200) {
        const src = img.src || img.dataset.src;
        if (src && src.startsWith("http")) {
          result.detail.push(src);
        }
      }
    });
    return result;
  }

  // 중복 제거
  function dedupe(arr) {
    return [...new Set(arr)];
  }

  // 메시지 리스너
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.action === "detectPlatform") {
      sendResponse({ platform: detectPlatform() });
      return;
    }

    if (msg.action === "extractImages") {
      const platform = detectPlatform();
      let result;

      switch (platform) {
        case "coupang":
          result = extractCoupang();
          break;
        case "naver":
          result = extractNaver();
          break;
        case "cafe24":
          result = extractCafe24();
          break;
        default:
          result = extractGeneric();
      }

      result.detail = dedupe(result.detail);
      result.main = dedupe(result.main);
      result.platform = platform;
      result.url = location.href;
      result.title = document.title;

      sendResponse(result);
      return;
    }

    // 펼쳐보기 후 재추출 (딜레이 필요한 경우)
    if (msg.action === "extractAfterExpand") {
      setTimeout(() => {
        const platform = detectPlatform();
        let result;
        switch (platform) {
          case "coupang": result = extractCoupang(); break;
          case "naver": result = extractNaver(); break;
          case "cafe24": result = extractCafe24(); break;
          default: result = extractGeneric();
        }
        result.detail = dedupe(result.detail);
        result.main = dedupe(result.main);
        result.platform = platform;
        result.url = location.href;
        result.title = document.title;
        sendResponse(result);
      }, 2000);
      return true; // async response
    }
  });
})();
