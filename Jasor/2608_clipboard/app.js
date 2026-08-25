const SERVER_URL = "http://127.0.0.1:8765";
const LAUNCHER_URL = "http://127.0.0.1:8764";
const POLL_MS = 2000;
const INSTALL_COMMAND = "pip install Pillow";
const START_COMMAND = "pythonw clipboard_backend.pyw";

let entries = [];
let selectedId = null;
let backendConnected = false;
let monitorEnabled = false;

const els = {
  backendBadge: document.getElementById("backendBadge"),
  backendHint: document.getElementById("backendHint"),
  btnConnect: document.getElementById("btnConnect"),
  btnCopyInstall: document.getElementById("btnCopyInstall"),
  btnCopyStart: document.getElementById("btnCopyStart"),
  btnClear: document.getElementById("btnClear"),
  btnClearClipboard: document.getElementById("btnClearClipboard"),
  autoWatch: document.getElementById("autoWatch"),
  status: document.getElementById("status"),
  historyList: document.getElementById("historyList"),
  historyCount: document.getElementById("historyCount"),
  textView: document.getElementById("textView"),
  imageView: document.getElementById("imageView"),
  emptyView: document.getElementById("emptyView"),
  textContent: document.getElementById("textContent"),
  imageContent: document.getElementById("imageContent"),
  imageInfo: document.getElementById("imageInfo"),
};

function init() {
  bindEvents();
  connectBackend({ autoStartMonitor: false, tryWakeLauncher: false });
}

function bindEvents() {
  els.btnConnect.addEventListener("click", () => connectBackend({ autoStartMonitor: true, tryWakeLauncher: true }));
  els.btnClear.addEventListener("click", () => clearHistory());
  els.btnClearClipboard.addEventListener("click", () => clearSystemClipboard());
  els.btnCopyInstall.addEventListener("click", () => copyText(INSTALL_COMMAND, "安装命令已复制"));
  els.btnCopyStart.addEventListener("click", () => copyText(START_COMMAND, "启动命令已复制"));
  els.autoWatch.addEventListener("change", () => toggleMonitor());
  window.addEventListener("pagehide", () => stopKeepalive());
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") {
      /* 页面隐藏后停止心跳，约 90 秒后 server 空闲退出 */
      stopKeepalive();
    } else if (backendConnected) {
      startKeepalive();
      pingHealth();
    }
  });
}

let pollTimer;

function startKeepalive() {
  stopKeepalive();
  pollTimer = window.setInterval(() => {
    if (!backendConnected) return;
    if (monitorEnabled) {
      refreshHistory(false);
    } else {
      pingHealth();
    }
  }, POLL_MS);
}

function stopKeepalive() {
  if (pollTimer !== undefined) {
    window.clearInterval(pollTimer);
    pollTimer = undefined;
  }
}

async function pingHealth() {
  try {
    const response = await fetch(`${SERVER_URL}/api/health`);
    if (!response.ok) {
      backendConnected = false;
      monitorEnabled = false;
      els.autoWatch.checked = false;
      stopKeepalive();
      updateBackendUi();
      setStatus("本地后台已断开（可能已空闲退出）");
    }
  } catch (_e) {
    backendConnected = false;
    monitorEnabled = false;
    els.autoWatch.checked = false;
    stopKeepalive();
    updateBackendUi();
    setStatus("本地后台已断开（可能已空闲退出）");
  }
}

async function connectBackend(options = {}) {
  setStatus("正在连接本地后台...");
  let connected = await checkHealth();
  if (!connected && options.tryWakeLauncher) connected = await wakeLauncher();
  if (!connected) {
    backendConnected = false;
    monitorEnabled = false;
    els.autoWatch.checked = false;
    stopKeepalive();
    updateBackendUi();
    setStatus("未连接：请先下载并运行 clipboard_backend.py");
    return;
  }
  backendConnected = true;
  updateBackendUi();
  startKeepalive();
  await refreshHistory(true);
  if (options.autoStartMonitor || els.autoWatch.checked) await startMonitor();
  setStatus(`已连接，历史 ${entries.length} 条（关页面约 90 秒后后台自动退出）`);
}

async function checkHealth() {
  try {
    const response = await fetch(`${SERVER_URL}/api/health`);
    if (!response.ok) return false;
    const payload = await response.json();
    monitorEnabled = Boolean(payload.monitoring);
    els.autoWatch.checked = monitorEnabled;
    return Boolean(payload.ok);
  } catch (_e) {
    return false;
  }
}

async function wakeLauncher() {
  try {
    const response = await fetch(`${LAUNCHER_URL}/start`);
    if (!response.ok) return false;
    const payload = await response.json();
    if (!payload.serverRunning) return false;
    await sleep(400);
    return checkHealth();
  } catch (_e) {
    return false;
  }
}

async function toggleMonitor() {
  if (!els.autoWatch.checked) { await stopMonitor(); return; }
  if (!backendConnected) { await connectBackend({ autoStartMonitor: true, tryWakeLauncher: true }); return; }
  await startMonitor();
}

async function startMonitor() {
  if (!backendConnected) {
    const ok = await checkHealth() || await wakeLauncher();
    if (!ok) { els.autoWatch.checked = false; setStatus("请先运行 python clipboard_backend.py --launcher"); return; }
    backendConnected = true;
  }
  try {
    const response = await fetch(`${SERVER_URL}/api/monitor/start`, { method: "POST" });
    const payload = await response.json();
    monitorEnabled = Boolean(payload.monitoring);
    els.autoWatch.checked = monitorEnabled;
    startKeepalive();
    updateBackendUi();
    setStatus("自动监控已开启");
  } catch (error) {
    els.autoWatch.checked = false;
    setStatus(`启动失败: ${error.message}`);
  }
}

async function stopMonitor() {
  if (backendConnected) {
    try { await fetch(`${SERVER_URL}/api/monitor/stop`, { method: "POST" }); } catch (_e) {}
  }
  monitorEnabled = false;
  if (backendConnected) startKeepalive();
  setStatus("自动监控已关闭（页面仍保持连接）");
}

async function refreshHistory(selectFirst) {
  if (!backendConnected) return;
  try {
    const response = await fetch(`${SERVER_URL}/api/history`);
    if (!response.ok) throw new Error("history failed");
    const payload = await response.json();
    const next = Array.isArray(payload.entries) ? payload.entries : [];
    const changed = next.length !== entries.length || next[0]?.id !== entries[0]?.id;
    entries = next;
    renderHistory();
    if ((selectFirst || changed) && entries.length > 0) {
      selectedId = entries[0].id;
      renderHistory();
      await showEntryById(entries[0].id);
    }
  } catch (error) {
    setStatus(`刷新失败: ${error.message}`);
  }
}

async function showEntryById(entryId) {
  const summary = entries.find((e) => e.id === entryId);
  if (!summary) return;
  if (summary.contentType === "text") { showTextEntry(summary); return; }
  const response = await fetch(`${SERVER_URL}/api/entry/${entryId}`);
  showImageEntry(await response.json());
}

function showTextEntry(entry) {
  els.emptyView.classList.add("hidden");
  els.imageView.classList.add("hidden");
  els.textView.classList.remove("hidden");
  els.textContent.textContent = entry.text || "";
  setStatus(`文本 | ${(entry.text || "").length} 字符`);
}

function showImageEntry(entry) {
  els.emptyView.classList.add("hidden");
  els.textView.classList.add("hidden");
  els.imageView.classList.remove("hidden");
  els.imageContent.src = entry.imageDataUrl || `${SERVER_URL}${entry.imageUrl || ""}`;
  els.imageInfo.textContent = `截图 ${entry.width || "?"}×${entry.height || "?"}`;
  setStatus("截图");
}

function renderHistory() {
  els.historyList.innerHTML = "";
  els.historyCount.textContent = `${entries.length} 条`;
  entries.forEach((entry) => {
    const li = document.createElement("li");
    li.className = `history-item${entry.id === selectedId ? " active" : ""}`;
    li.innerHTML = `<div class="history-meta"><span>${formatTime(entry.createdAt)}</span><span class="history-type">${entry.contentType === "image" ? "截图" : "文本"}</span></div><div class="history-preview">${escapeHtml(entry.preview || "")}</div>`;
    li.addEventListener("click", async () => { selectedId = entry.id; renderHistory(); await showEntryById(entry.id); });
    els.historyList.appendChild(li);
  });
}

async function clearHistory() {
  if (!entries.length) { setStatus("历史已是空的"); return; }
  if (!window.confirm("确定清空本软件的历史记录吗？\n（不会清空系统剪切板）")) return;
  if (!backendConnected) { setStatus("请先连接后台"); return; }
  await fetch(`${SERVER_URL}/api/history/clear`, { method: "POST" });
  entries = [];
  selectedId = null;
  renderHistory();
  els.textContent.textContent = "";
  els.imageContent.src = "";
  els.textView.classList.add("hidden");
  els.imageView.classList.add("hidden");
  els.emptyView.classList.remove("hidden");
  setStatus("历史已清空（系统剪切板未改动）");
}

async function clearSystemClipboard() {
  if (!backendConnected) { setStatus("请先连接后台"); return; }
  if (!window.confirm("确定清空系统剪切板吗？\n清空后其他软件也无法再粘贴当前内容。")) return;
  try {
    const response = await fetch(`${SERVER_URL}/api/clipboard/clear`, { method: "POST" });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "清空失败");
    }
    setStatus("系统剪切板已清空");
  } catch (error) {
    setStatus(`清空系统剪切板失败: ${error.message}`);
  }
}

function updateBackendUi() {
  if (backendConnected) {
    els.backendBadge.textContent = monitorEnabled ? "本地后台：监控中" : "本地后台：已连接";
    els.backendBadge.className = "badge online";
    els.backendHint.classList.add("hidden");
  } else {
    els.backendBadge.textContent = "本地后台：未连接";
    els.backendBadge.className = "badge offline";
    els.backendHint.classList.remove("hidden");
  }
}

async function copyText(text, okMessage) {
  try { await navigator.clipboard.writeText(text); setStatus(okMessage); }
  catch (_e) { setStatus(text); }
}

function setStatus(msg) { els.status.textContent = msg; }
function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }
function formatTime(iso) {
  const d = new Date(iso);
  return `${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")} ${String(d.getHours()).padStart(2,"0")}:${String(d.getMinutes()).padStart(2,"0")}:${String(d.getSeconds()).padStart(2,"0")}`;
}
function escapeHtml(v) { return v.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }

init();
