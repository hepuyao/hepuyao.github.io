import { computeCityStatus, ymd } from "./status.js";

const CITIES = ["北京", "天津"];

function parseIso(s) {
  return new Date(s);
}

function formatRange(start, end) {
  if (!start || !end) return "—";
  return `${ymd(start)} ~ ${ymd(end)}`;
}

function renderCard(city, data, today) {
  const el = document.createElement("section");
  el.className = "card";
  const cityData = data.cities && data.cities[city];
  const title = document.createElement("h2");
  title.textContent = city;
  el.appendChild(title);
  if (!cityData) {
    const p = document.createElement("p");
    p.className = "status";
    p.textContent = "暂无数据";
    el.appendChild(p);
    return el;
  }
  const ref = (data.reference && data.reference[city]) || null;
  const status = computeCityStatus(
    today,
    parseIso(cityData.signupStart),
    parseIso(cityData.signupEnd),
    ref ? parseIso(ref.signupStart) : null,
    ref ? parseIso(ref.signupEnd) : null,
    ref ? ref.batchName : "",
  );
  const range = document.createElement("p");
  range.className = "range";
  range.textContent =
    status.kind === "estimated"
      ? `估算报名区间：${formatRange(status.rangeStart, status.rangeEnd)}`
      : `报名有效时间：${formatRange(parseIso(cityData.signupStart), parseIso(cityData.signupEnd))}`;
  el.appendChild(range);
  const statusEl = document.createElement("p");
  statusEl.className = "status";
  statusEl.textContent = status.message;
  el.appendChild(statusEl);
  if (status.note) {
    const note = document.createElement("p");
    note.className = "note";
    note.textContent = status.note;
    el.appendChild(note);
  }
  return el;
}

async function main() {
  const cards = document.getElementById("cards");
  const error = document.getElementById("error");
  try {
    const res = await fetch("./data.json", { cache: "no-store" });
    if (!res.ok) throw new Error("bad status");
    const data = await res.json();
    document.getElementById("batchLine").textContent = data.batch
      ? `当前批次：${data.batch.name}`
      : "";
    document.getElementById("updatedAt").textContent = data.updatedAt
      ? `数据更新：${data.updatedAt}`
      : "";
    if (data.source) document.getElementById("sourceLink").href = data.source;
    const today = new Date();
    cards.innerHTML = "";
    for (const city of CITIES) cards.appendChild(renderCard(city, data, today));
  } catch (e) {
    error.hidden = false;
    cards.innerHTML = "";
  }
}

main();
