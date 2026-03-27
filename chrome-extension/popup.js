/**
 * Popup UI 로직
 */

const extractBtn = document.getElementById("extractBtn");
const downloadBtn = document.getElementById("downloadBtn");
const statusArea = document.getElementById("statusArea");
const progressArea = document.getElementById("progressArea");
const imageList = document.getElementById("imageList");
const platformArea = document.getElementById("platformArea");
const warningArea = document.getElementById("warningArea");

let extractedData = null;

// 초기화: 플랫폼 감지
document.addEventListener("DOMContentLoaded", async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  try {
    const response = await chrome.tabs.sendMessage(tab.id, { action: "detectPlatform" });
    showPlatform(response.platform);
  } catch (e) {
    showPlatform("unknown");
    warningArea.innerHTML = `
      <div class="warning">
        지원되지 않는 사이트이거나 페이지가 아직 로딩 중입니다.<br>
        페이지 로딩 완료 후 다시 시도해주세요.
      </div>
    `;
  }
});

function showPlatform(platform) {
  const names = {
    coupang: "쿠팡",
    naver: "네이버 스마트스토어",
    cafe24: "카페24",
    unknown: "기타 사이트",
  };
  const cls = `platform-${platform}`;
  platformArea.innerHTML = `<span class="platform-badge ${cls}">${names[platform] || platform}</span>`;
}

// 추출 버튼
extractBtn.addEventListener("click", async () => {
  extractBtn.disabled = true;
  extractBtn.textContent = "추출 중...";
  progressArea.textContent = "상세페이지 이미지를 분석하고 있습니다...";

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  try {
    // 먼저 일반 추출 시도
    let response = await chrome.tabs.sendMessage(tab.id, { action: "extractImages" });

    // 펼쳐보기가 필요했으면 딜레이 후 재추출
    if (response.expandNeeded) {
      progressArea.textContent = "상세페이지 펼치는 중... (2초 대기)";
      response = await chrome.tabs.sendMessage(tab.id, { action: "extractAfterExpand" });
    }

    extractedData = response;
    showResults(response);
  } catch (e) {
    statusArea.innerHTML = `<span style="color:#e74c3c">추출 실패: ${e.message}</span>`;
    extractBtn.disabled = false;
    extractBtn.textContent = "다시 시도";
  }
});

function showResults(data) {
  const detailCount = data.detail.length;
  const mainCount = data.main.length;
  const total = detailCount + mainCount;

  statusArea.innerHTML = `
    상세페이지 이미지: <span class="count">${detailCount}</span>개<br>
    메인 상품 이미지: <span class="count">${mainCount}</span>개<br>
    <small style="color:#95a5a6">총 ${total}개 이미지 발견</small>
  `;

  if (total > 0) {
    downloadBtn.style.display = "block";
    downloadBtn.textContent = `전체 다운로드 (${total}개)`;
    showImageList(data);
  } else {
    statusArea.innerHTML += `
      <br><br>
      <span style="color:#e67e22">
        이미지를 찾지 못했습니다.<br>
        상세페이지가 펼쳐져 있는지 확인해주세요.
      </span>
    `;
  }

  extractBtn.disabled = false;
  extractBtn.textContent = "다시 추출하기";
  progressArea.textContent = "";
}

function showImageList(data) {
  imageList.style.display = "block";
  imageList.innerHTML = "";

  const allImages = [
    ...data.main.map((url) => ({ url, type: "main" })),
    ...data.detail.map((url) => ({ url, type: "detail" })),
  ];

  allImages.forEach((img, i) => {
    const item = document.createElement("div");
    item.className = "image-item";
    const label = img.type === "main" ? "메인" : "상세";
    item.innerHTML = `
      <img src="${img.url}" onerror="this.style.display='none'">
      <div class="info">
        <div>${label} #${i + 1}</div>
        <div class="size">${truncateUrl(img.url)}</div>
      </div>
    `;
    imageList.appendChild(item);
  });
}

function truncateUrl(url) {
  try {
    const u = new URL(url);
    const path = u.pathname;
    return path.length > 40 ? "..." + path.slice(-40) : path;
  } catch {
    return url.slice(0, 40) + "...";
  }
}

// 다운로드 버튼
downloadBtn.addEventListener("click", () => {
  if (!extractedData) return;

  const allImages = [
    ...extractedData.main.map((url) => ({ url, type: "main" })),
    ...extractedData.detail.map((url) => ({ url, type: "detail" })),
  ];

  // 폴더명 생성
  const platform = extractedData.platform || "site";
  const timestamp = new Date().toISOString().slice(0, 10);
  const folderName = `${platform}_${timestamp}`;

  chrome.runtime.sendMessage({
    action: "downloadImages",
    images: allImages,
    folderName: folderName,
  });

  downloadBtn.textContent = "다운로드 시작됨!";
  downloadBtn.disabled = true;
  progressArea.textContent = `${allImages.length}개 이미지를 다운로드 폴더에 저장 중...`;

  setTimeout(() => {
    downloadBtn.disabled = false;
    downloadBtn.textContent = `다시 다운로드 (${allImages.length}개)`;
    progressArea.textContent = "다운로드 완료!";
  }, 3000);
});
