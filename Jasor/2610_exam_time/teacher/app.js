function physicsLabel(p) {
  if (!p || !p.found) return "未发现物理岗";
  return (p.posts || []).map((x) => x.name).filter(Boolean).join("；") || "发现物理相关岗位";
}
function signupLabel(s) {
  if (!s || !s.found) return "报名时间未解析到";
  if (s.start && s.end) return `${s.start} ~ ${s.end}`;
  return s.raw || "报名时间未解析到";
}
async function main() {
  const list = document.getElementById("list");
  const error = document.getElementById("error");
  try {
    const res = await fetch("./data.json", { cache: "no-store" });
    if (!res.ok) throw new Error("bad");
    const data = await res.json();
    document.getElementById("updatedAt").textContent = data.updatedAt
      ? `数据更新：${data.updatedAt}` : "";
    if (data.source) document.getElementById("sourceLink").href = data.source;
    list.innerHTML = "";
    for (const item of data.items || []) {
      const el = document.createElement("article");
      el.className = "card";
      const a = document.createElement("a");
      a.href = item.url || "#";
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.textContent = item.title || "（无标题）";
      const meta = document.createElement("p");
      meta.className = "meta";
      meta.textContent = `发布：${item.publishedAt || "—"}`;
      const signup = document.createElement("p");
      signup.textContent = `报名：${signupLabel(item.signup)}`;
      const phys = document.createElement("p");
      phys.textContent = `物理：${physicsLabel(item.physics)}`;
      el.append(a, meta, signup, phys);
      list.appendChild(el);
    }
  } catch (e) {
    error.hidden = false;
  }
}
main();
