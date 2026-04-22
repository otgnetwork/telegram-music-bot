const tg = window.Telegram?.WebApp;

if (tg) {
  tg.ready();
  tg.expand();
}

const MAIN_BOT_URL = "https://t.me/otgmusicbot";
const TIKTOK_URL = "https://www.tiktok.com/@alexey_pv_";

const homeScreen = document.getElementById("homeScreen");
const musicScreen = document.getElementById("musicScreen");
const clipsScreen = document.getElementById("clipsScreen");
const songScreen = document.getElementById("songScreen");

const openMusicBtn = document.getElementById("openMusicBtn");
const openClipsBtn = document.getElementById("openClipsBtn");
const openSongBtn = document.getElementById("openSongBtn");
const openLiveBtn = document.getElementById("openLiveBtn");

const backFromMusic = document.getElementById("backFromMusic");
const backFromClips = document.getElementById("backFromClips");
const backFromSong = document.getElementById("backFromSong");

const musicSearchForm = document.getElementById("musicSearchForm");
const musicQuery = document.getElementById("musicQuery");
const musicStatus = document.getElementById("musicStatus");
const musicResults = document.getElementById("musicResults");
const tagButtons = document.querySelectorAll(".tag-btn");
const openMainBotBtn = document.getElementById("openMainBotBtn");

function showScreen(screen) {
  [homeScreen, musicScreen, clipsScreen, songScreen].forEach((item) => {
    item.classList.remove("active");
  });
  screen.classList.add("active");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function setMusicStatus(text, className = "") {
  musicStatus.textContent = text;
  musicStatus.className = "status-box";
  if (className) {
    musicStatus.classList.add(className);
  }
}

function renderMusicResults(items) {
  musicResults.innerHTML = "";

  if (!items.length) {
    setMusicStatus("Ничего не найдено. Попробуй другой запрос.", "error");
    return;
  }

  setMusicStatus(`Найдено результатов: ${items.length}`);

  items.forEach((item) => {
    const card = document.createElement("div");
    card.className = "result-card";

    const artwork = item.artwork_url
      ? `<img class="result-cover" src="${item.artwork_url}" alt="${escapeHtml(item.title)}" />`
      : `<div class="result-cover"></div>`;

    card.innerHTML = `
      <div class="result-top">
        ${artwork}
        <div class="result-meta">
          <h3 class="result-title">${escapeHtml(item.title)}</h3>
          <p class="result-artist">${escapeHtml(item.artist)}</p>
        </div>
      </div>
      <div class="audio-wrap">
        <audio controls preload="none" src="${item.preview_url}"></audio>
      </div>
    `;

    musicResults.appendChild(card);
  });
}

async function searchMusic(query) {
  const value = query.trim();

  if (!value) {
    setMusicStatus("Введите название трека или исполнителя.", "error");
    musicResults.innerHTML = "";
    return;
  }

  setMusicStatus("Ищу музыку...", "loading");
  musicResults.innerHTML = "";

  try {
    const response = await fetch(`/api/search?q=${encodeURIComponent(value)}`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    renderMusicResults(Array.isArray(data) ? data : []);
  } catch (error) {
    console.error("Music search error:", error);
    setMusicStatus("Ошибка поиска. Попробуй ещё раз позже.", "error");
  }
}

function openTelegramLink(url) {
  if (tg && typeof tg.openTelegramLink === "function") {
    tg.openTelegramLink(url);
    return;
  }
  window.open(url, "_blank");
}

function openExternal(url) {
  if (tg && typeof tg.openLink === "function") {
    tg.openLink(url);
    return;
  }
  window.open(url, "_blank");
}

openMusicBtn.addEventListener("click", () => {
  showScreen(musicScreen);
  setTimeout(() => musicQuery.focus(), 150);
});

openClipsBtn.addEventListener("click", () => {
  showScreen(clipsScreen);
});

openSongBtn.addEventListener("click", () => {
  showScreen(songScreen);
});

openLiveBtn.addEventListener("click", () => {
  openExternal(TIKTOK_URL);
});

backFromMusic.addEventListener("click", () => showScreen(homeScreen));
backFromClips.addEventListener("click", () => showScreen(homeScreen));
backFromSong.addEventListener("click", () => showScreen(homeScreen));

musicSearchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await searchMusic(musicQuery.value);
});

tagButtons.forEach((button) => {
  button.addEventListener("click", async () => {
    const query = button.dataset.query || "";
    musicQuery.value = query;
    await searchMusic(query);
  });
});

openMainBotBtn.addEventListener("click", () => {
  openTelegramLink(MAIN_BOT_URL);
});