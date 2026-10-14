# 软考报名倒计时（北京 / 天津）

日期：2026-10-14  
状态：已对齐需求，待实现

## 目标

在 `Jasor/2610_exam_time/ruankao/` 提供静态页，展示北京、天津距离软考报名窗口的状态：

- 未开始：还剩 N 天
- 进行中：报名进行中，报名截止日期为 YYYY-MM-DD
- 已结束且官网尚无下一批次窗口：按历史同半年窗口 +1 年估算，显示「大约还剩 N 天」，并注明参考批次

数据必须来自官网 https://bm.ruankao.org.cn/sign/welcome，经 GitHub Actions **每天 1 次**抓取写入 JSON；页面只读 JSON，不直连官网（避免 GitHub Pages CORS）。

## 非目标

- 本机常驻 Python 实时代理
- 展示全国其他省份
- 秒级实时（接受日更）
- 缴费时间倒计时（仅报名有效时间）
- 报名入口登录/跳转业务

## 方案

脚本抓取 + 精简 JSON + 前端按当天日期算状态（方案 A）。

## 目录结构

```
Jasor/2610_exam_time/ruankao/
  index.html
  app.js
  style.css
  data.json
  fetch_ruankao.py
  README.md

.github/workflows/ruankao-exam-time.yml
```

`Jasor/README.md` 增加入口链接。

## 数据流

```
GitHub Actions (每日 / 手动)
        |
        v
 fetch_ruankao.py  -->  POST/GET 官网 welcome
        |
        v
  data.json (commit if changed)
        |
        v
  index.html + app.js  按本地「今天」渲染北京/天津
```

本地也可：`cd Jasor/2610_exam_time/ruankao && python3 fetch_ruankao.py`。

## JSON 契约

```json
{
  "updatedAt": "2026-10-14T10:00:00+08:00",
  "source": "https://bm.ruankao.org.cn/sign/welcome",
  "batch": {
    "id": "...",
    "name": "2026年下半年软考"
  },
  "cities": {
    "北京": {
      "signupStart": "2026-09-11T00:00:00+08:00",
      "signupEnd": "2026-09-17T23:59:00+08:00",
      "estimated": false
    },
    "天津": {
      "signupStart": "2026-08-27T09:00:00+08:00",
      "signupEnd": "2026-09-16T17:00:00+08:00",
      "estimated": false
    }
  },
  "reference": {
    "北京": {
      "signupStart": "2026-03-27T00:00:00+08:00",
      "signupEnd": "2026-04-02T23:59:00+08:00",
      "batchName": "2026年上半年软考"
    },
    "天津": {
      "signupStart": "2026-03-20T09:00:00+08:00",
      "signupEnd": "2026-04-15T17:00:00+08:00",
      "batchName": "2026年上半年软考"
    }
  }
}
```

### 抓取规则

1. 考试批次取官网下拉列表**第一项**（最近/当前批次）。
2. 从该批次机构列表解析「北京」「天津」的**报名有效时间**起止。
3. `reference`：用于「当前窗口已结束」时的估算基准  
   - 若当前批次名为「下半年」→ 取最近一次「上半年」同城窗口  
   - 若当前批次名为「上半年」→ 取最近一次「下半年」同城窗口（供上半年结束后、下半年未上线时使用）
4. 时间统一存 ISO 8601，东八区。

### 前端状态（每城独立）

以本地日历「今天」与 `signupStart` / `signupEnd` 的日期比较（按自然日）：

| 条件 | 展示 |
|------|------|
| 今天 &lt; 开始日 | `还剩 N 天`（到开始日） |
| 开始日 ≤ 今天 ≤ 截止日 | `报名进行中，报名截止日期为 YYYY-MM-DD` |
| 今天 &gt; 截止日 | 将 `reference` 起止整体 +1 年得到估算窗口；文案 `大约还剩 N 天`；注明「参考 {batchName} 推算」；界面可标记为估算 |

天数：到「报名开始日」的自然日差（非负整数）。估算时：`reference` 起止先整体 +1 年；若估算开始日仍早于今天，再整体 +1 年；最多相对 reference 推两年。若仍早于今天，显示「暂无法估算下一批次」。

## 页面 UI

- 标题：软考报名倒计时（北京 / 天津）
- 两块：北京、天津（桌面并排，窄屏上下）
- 每块：机构名、批次名、报名区间、状态主文案
- 底部：`updatedAt`、官网链接
- 风格：与现有 Jasor 工具页一致，简洁可读

## GitHub Actions

文件：`.github/workflows/ruankao-exam-time.yml`

- `schedule`: `0 2 * * *`（UTC，约北京时间 10:00）
- `workflow_dispatch` 支持手动触发
- 步骤：checkout → `python3 Jasor/2610_exam_time/ruankao/fetch_ruankao.py` → 若 `data.json` 变更则 commit + push
- commit message：`chore(ruankao): update exam signup data`

## 错误处理

| 场景 | 行为 |
|------|------|
| 抓取失败 | 不覆盖已有 `data.json`；Actions 失败退出 |
| 某城缺失 | 该城「暂无数据」 |
| 已结束但无 reference | 「暂无法估算下一批次」 |
| 页面加载 JSON 失败 | 「数据加载失败，请稍后刷新」 |

## 成功标准

1. 打开 `ruankao/index.html` 可见北京、天津状态文案。
2. 在「下半年报名已结束」的日期下，显示基于上半年 +1 年的「大约还剩 N 天」。
3. 本地跑 `fetch_ruankao.py` 能更新 `data.json`。
4. Actions 每日可更新；失败不抹掉旧数据。
5. `Jasor/README.md` 有入口链接。
