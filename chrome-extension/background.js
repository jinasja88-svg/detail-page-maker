/**
 * Background Service Worker
 * 이미지 다운로드를 처리한다.
 */

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === "downloadImages") {
    downloadAllImages(msg.images, msg.folderName);
    sendResponse({ status: "started" });
  }
});

async function downloadAllImages(images, folderName) {
  const folder = folderName || "detail_page_images";

  for (let i = 0; i < images.length; i++) {
    const url = images[i].url;
    const type = images[i].type; // "detail" or "main"
    const ext = getExtension(url);
    const filename = `${folder}/${type}_${String(i + 1).padStart(3, "0")}${ext}`;

    try {
      await chrome.downloads.download({
        url: url,
        filename: filename,
        conflictAction: "uniquify",
      });
    } catch (e) {
      console.error(`Download failed: ${url}`, e);
    }
  }
}

function getExtension(url) {
  const path = new URL(url).pathname.toLowerCase();
  if (path.includes(".png")) return ".png";
  if (path.includes(".jpg") || path.includes(".jpeg")) return ".jpg";
  if (path.includes(".gif")) return ".gif";
  if (path.includes(".webp")) return ".webp";
  return ".jpg";
}
