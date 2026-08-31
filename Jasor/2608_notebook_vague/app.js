(() => {
  const STORAGE_KEY = "jasor.notebook_vague.web.v1";
  const API_BASE = "http://127.0.0.1:18766";
  const POLL_MS = 400;

  const defaultConfig = {
    hoverOpacity: 0.96,
    leaveOpacity: 0.45,
    leaveBlur: 10,
    hideAwayText: true,
    noteText: "",
  };

  const notebook = document.getElementById("notebook");
  const editor = document.getElementById("editor");
  const statusText = document.getElementById("statusText");
  const charCount = document.getElementById("charCount");
  const syncBadge = document.getElementById("syncBadge");
  const backendHint = document.getElementById("backendHint");
  const btnCopyStart = document.getElementById("btnCopyStart");
  const btnConnect = document.getElementById("btnConnect");
  const btnSettings = document.getElementById("btnSettings");
  const btnClear = document.getElementById("btnClear");
  const btnReveal = document.getElementById("btnReveal");
  const dialog = document.getElementById("settingsDialog");
  const START_COMMAND = "pip3 install -r requirements.txt && python3 note_backend.py";
  const FETCH_OPTS = { cache: "no-store", mode: "cors" };
  const form = document.getElementById("settingsForm");
  const hoverOpacity = document.getElementById("hoverOpacity");
  const leaveBlur = document.getElementById("leaveBlur");
  const leaveOpacity = document.getElementById("leaveOpacity");
  const hideAwayText = document.getElementById("hideAwayText");
  const hoverOpacityVal = document.getElementById("hoverOpacityVal");
  const leaveBlurVal = document.getElementById("leaveBlurVal");
  const leaveOpacityVal = document.getElementById("leaveOpacityVal");

  let config = loadConfig();
  let isHover = false;
  let isRevealing = false;
  let backendOnline = false;
  let remoteRev = 0;
  let applyingRemote = false;
  let pushTimer = null;
  let lastLocalEditAt = 0;

  function loadConfig() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        return { ...defaultConfig };
      }
      return { ...defaultConfig, ...JSON.parse(raw) };
    } catch (err) {
      return { ...defaultConfig };
    }
  }

  function saveConfig() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
  }

  function applyCssVars() {
    const root = document.documentElement;
    root.style.setProperty("--hover-opacity", String(config.hoverOpacity));
    root.style.setProperty("--leave-opacity", String(config.leaveOpacity));
    root.style.setProperty("--leave-blur", `${config.leaveBlur}px`);
  }

  function updateStatus() {
    charCount.textContent = String(editor.value.length);
    if (syncBadge) {
      syncBadge.textContent = backendOnline ? "本地：已连接" : "本地：未连接";
      syncBadge.classList.toggle("online", backendOnline);
      syncBadge.classList.toggle("offline", !backendOnline);
    }
    if (backendHint) {
      backendHint.classList.toggle("hidden", backendOnline);
      backendHint.hidden = backendOnline;
    }
    if (btnConnect) {
      btnConnect.hidden = backendOnline;
    }
    document.body.classList.toggle("is-online", backendOnline);
    document.body.classList.toggle("is-offline", !backendOnline);
    statusText.textContent = "";
  }

  function setHover(next) {
    isHover = next;
    notebook.classList.toggle("is-hover", next);
    notebook.classList.toggle("is-away", !next);
    notebook.classList.toggle("hide-text", !next && config.hideAwayText && !isRevealing);
    notebook.classList.toggle("is-revealing", isRevealing);
    updateStatus();
  }

  function syncSettingsForm() {
    hoverOpacity.value = String(config.hoverOpacity);
    leaveBlur.value = String(config.leaveBlur);
    leaveOpacity.value = String(config.leaveOpacity);
    hideAwayText.checked = Boolean(config.hideAwayText);
    hoverOpacityVal.textContent = config.hoverOpacity.toFixed(2);
    leaveBlurVal.textContent = `${config.leaveBlur}px`;
    leaveOpacityVal.textContent = config.leaveOpacity.toFixed(2);
  }

  async function fetchNote() {
    const res = await fetch(`${API_BASE}/api/note`, { method: "GET", ...FETCH_OPTS });
    if (!res.ok) {
      throw new Error("fetch note failed");
    }
    return res.json();
  }

  async function pushNote(text) {
    const res = await fetch(`${API_BASE}/api/note`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
      ...FETCH_OPTS,
    });
    if (!res.ok) {
      throw new Error("push note failed");
    }
    return res.json();
  }

  async function pingBackend() {
    try {
      const res = await fetch(`${API_BASE}/api/health`, { method: "GET", ...FETCH_OPTS });
      backendOnline = res.ok;
    } catch (err) {
      backendOnline = false;
    }
    updateStatus();
    return backendOnline;
  }

  function schedulePush() {
    if (!backendOnline) {
      return;
    }
    if (pushTimer) {
      clearTimeout(pushTimer);
    }
    pushTimer = setTimeout(async () => {
      try {
        const data = await pushNote(editor.value);
        remoteRev = Number(data.rev) || remoteRev;
      } catch (err) {
        backendOnline = false;
        updateStatus();
      }
    }, 350);
  }

  async function pullIfNeeded() {
    const online = await pingBackend();
    if (!online) {
      return;
    }
    try {
      const data = await fetchNote();
      const rev = Number(data.rev) || 0;
      const text = String(data.text || "");
      if (rev <= remoteRev) {
        return;
      }
      const isEditingWeb = document.activeElement === editor;
      const quietMs = Date.now() - lastLocalEditAt;
      const canApplyRemote =
        text !== editor.value &&
        (!isEditingWeb || quietMs > 800) &&
        (text.length >= editor.value.length || quietMs > 1500);
      if (!canApplyRemote) {
        return;
      }
      applyingRemote = true;
      editor.value = text;
      config.noteText = text;
      saveConfig();
      remoteRev = rev;
      applyingRemote = false;
      updateStatus();
    } catch (err) {
      backendOnline = false;
      updateStatus();
    }
  }

  editor.value = config.noteText || "";
  applyCssVars();
  setHover(false);
  updateStatus();

  editor.addEventListener("input", () => {
    if (applyingRemote) {
      return;
    }
    lastLocalEditAt = Date.now();
    config.noteText = editor.value;
    saveConfig();
    updateStatus();
    schedulePush();
  });

  notebook.addEventListener("mouseenter", () => {
    setHover(true);
  });

  notebook.addEventListener("mouseleave", () => {
    if (!isRevealing) {
      setHover(false);
    }
  });

  editor.addEventListener("focus", () => {
    if (notebook.matches(":hover")) {
      setHover(true);
    }
  });

  btnReveal.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    isRevealing = true;
    notebook.classList.add("is-revealing");
    notebook.classList.remove("hide-text");
    updateStatus();
  });

  const endReveal = () => {
    isRevealing = false;
    notebook.classList.remove("is-revealing");
    setHover(notebook.matches(":hover"));
  };

  btnReveal.addEventListener("pointerup", endReveal);
  btnReveal.addEventListener("pointerleave", endReveal);
  btnReveal.addEventListener("pointercancel", endReveal);

  btnClear.addEventListener("click", async () => {
    if (!editor.value) {
      return;
    }
    if (!window.confirm("clear?")) {
      return;
    }
    editor.value = "";
    config.noteText = "";
    saveConfig();
    updateStatus();
    if (backendOnline) {
      try {
        const data = await pushNote("");
        remoteRev = Number(data.rev) || remoteRev;
      } catch (err) {
        // ignore
      }
    }
    editor.focus();
  });

  btnSettings.addEventListener("click", () => {
    syncSettingsForm();
    dialog.showModal();
  });

  if (btnCopyStart) {
    btnCopyStart.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(START_COMMAND);
        btnCopyStart.textContent = "已复制";
        setTimeout(() => {
          btnCopyStart.textContent = "复制启动命令";
        }, 1500);
      } catch (err) {
        window.prompt("复制以下命令到终端运行：", START_COMMAND);
      }
    });
  }

  if (btnConnect) {
    btnConnect.addEventListener("click", async () => {
      btnConnect.disabled = true;
      btnConnect.textContent = "连接中…";
      const ok = await pingBackend();
      btnConnect.disabled = false;
      btnConnect.textContent = "重试连接";
      if (ok) {
        try {
          const data = await fetchNote();
          remoteRev = Number(data.rev) || 0;
          const remoteText = String(data.text || "");
          if (remoteText && remoteText !== editor.value) {
            editor.value = remoteText;
            config.noteText = remoteText;
            saveConfig();
            updateStatus();
          }
        } catch (err) {
          // ignore
        }
      }
    });
  }

  hoverOpacity.addEventListener("input", () => {
    hoverOpacityVal.textContent = Number(hoverOpacity.value).toFixed(2);
  });
  leaveBlur.addEventListener("input", () => {
    leaveBlurVal.textContent = `${leaveBlur.value}px`;
  });
  leaveOpacity.addEventListener("input", () => {
    leaveOpacityVal.textContent = Number(leaveOpacity.value).toFixed(2);
  });

  form.addEventListener("submit", (event) => {
    const submitter = event.submitter;
    if (!submitter || submitter.value !== "ok") {
      return;
    }
    config.hoverOpacity = Number(hoverOpacity.value);
    config.leaveBlur = Number(leaveBlur.value);
    config.leaveOpacity = Number(leaveOpacity.value);
    config.hideAwayText = hideAwayText.checked;
    applyCssVars();
    saveConfig();
    setHover(notebook.matches(":hover"));
  });

  (async () => {
    const online = await pingBackend();
    if (online) {
      try {
        const data = await fetchNote();
        remoteRev = Number(data.rev) || 0;
        const remoteText = String(data.text || "");
        if (remoteText && remoteText !== editor.value) {
          // 远端有内容时优先用远端（助手是跨页同步源）
          if (!editor.value || remoteText.length >= editor.value.length) {
            editor.value = remoteText;
            config.noteText = remoteText;
            saveConfig();
          } else {
            await pushNote(editor.value);
          }
        } else if (editor.value && !remoteText) {
          const data2 = await pushNote(editor.value);
          remoteRev = Number(data2.rev) || remoteRev;
        }
        updateStatus();
      } catch (err) {
        // ignore
      }
    }
    setInterval(pullIfNeeded, POLL_MS);
  })();
})();
