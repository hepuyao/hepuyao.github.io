# 天津教招列表（中学 / 教育系统）— 最近 20 条

日期：2026-10-15  
状态：已对齐需求，待实现

## 目标

在 `Jasor/2610_exam_time/teacher/` 提供静态页，展示天津市人才服务中心栏目（`cate_id=3013`）中**最近 20 条**标题命中「中学 / 教育系统 / 教育局…」的招聘公告，并解析每条：

- 报名时间（起止或原文）
- 是否包含物理类教师岗位（及岗位摘要）

数据经 GitHub Actions **每天 1 次**抓取写入 `data.json`；页面只读 JSON（避免 GitHub Pages CORS）。

## 非目标

- 浏览器直连官网实时抓附件
- 只展示「已确认有物理」的公告（无物理也展示，标「未发现物理岗」）
- 全国其他省份、非 3013 栏目
- 自动报名 / 登录代填

## 方案

列表按标题筛选取最近 20 条 → 逐条深挖正文/附件 → 写入 JSON → 静态页展示（方案 A）。

## 目录结构

```
Jasor/2610_exam_time/teacher/
  index.html
  app.js
  style.css
  data.json
  fetch_teacher.py
  parse_teacher.py
  README.md

.github/workflows/teacher-jobs.yml
```

`Jasor/README.md` 增加入口链接。

## 数据流

```
GitHub Actions (每日 UTC 03:00 / 手动)
        |
        v
 fetch_teacher.py
   - 多关键词搜 3013 列表，合并去重
   - 按 publishedAt 降序取 20 条标题命中项
   - 逐条打开详情，下载 xls/xlsx，解析物理岗与报名时间
        |
        v
  data.json
        |
        v
  index.html + app.js  只读展示
```

## 标题命中规则

候选标题含以下任一子串即命中：

- `中学`
- `教育系统`
- `教育局`
- `高层次教育`
- `教育体育局`

可选排除（实现时写死，可调）：标题含 `幼儿园` 且不含上述中学/教育系统类关键词时跳过。

## JSON 契约

```json
{
  "updatedAt": "2026-10-15T11:00:00+08:00",
  "source": "https://www.tjtalents.com.cn/app/article/list/3013.shtml",
  "items": [
    {
      "title": "2026年红桥区教育系统公开招聘高层次人才",
      "publishedAt": "2026-08-03",
      "url": "https://zxbm.tjtalents.com.cn/...",
      "titleMatchedBy": ["教育系统"],
      "physics": {
        "found": false,
        "posts": []
      },
      "signup": {
        "found": false,
        "raw": null,
        "start": null,
        "end": null
      },
      "parseNotes": []
    }
  ]
}
```

### 物理岗解析

1. 优先下载详情页中的 `.xls` / `.xlsx` 招聘计划，整表转文本；行内含「物理」且像岗位（教师 / 专技 / 学科教学等）→ 写入 `posts`（尽量提取岗位名、人数、学校/单位、教师资格提示）。
2. 正文 HTML 出现「物理教师」「物理学科」等也计为发现。
3. 都没有 → `physics.found = false`；页面文案：**未发现物理岗**。

### 报名时间解析

1. 在正文与附件文本中查找「报名时间」「网上报名」「报名起止」等附近的日期时间段。
2. 能解析则填 ISO `start` / `end`（东八区）；否则保留 `raw` 原文片段。
3. 都没有 → `signup.found = false`；页面文案：**报名时间未解析到**。

### WebList / 解析失败

详情为前端壳页或无附件时：尝试同页可发现的附件/详情链接；仍失败则该条保留在 20 条内，物理/报名按未发现处理，`parseNotes` 记录原因。单条失败不中断整批。

## 页面 UI

- 标题：天津教招（中学 / 教育系统）最近 20 条
- 每条：标题（外链）、发布日、报名时间、物理岗摘要
- 底部：`updatedAt`、源列表链接
- 风格与 `ruankao` / Jasor 工具页一致

## GitHub Actions

文件：`.github/workflows/teacher-jobs.yml`

- `schedule`: `0 3 * * *`（UTC，约北京时间 11:00）
- `workflow_dispatch`
- 步骤：checkout → `pip install xlrd`（及解析 xlsx 所需最小依赖，若用）→ `python3 Jasor/2610_exam_time/teacher/fetch_teacher.py` → 若 `data.json` 变更则 commit + push
- commit message：`chore(teacher): update job listings`

列表接口失败时不覆盖已有 `data.json`，以非 0 退出。

## 成功标准

1. 打开 `teacher/index.html` 可见最多 20 条标题命中公告。
2. 每条展示报名时间或「报名时间未解析到」、物理岗摘要或「未发现物理岗」。
3. 本地 `fetch_teacher.py` 可更新 `data.json`。
4. Actions 每日可更新；失败不抹掉旧数据。
5. `Jasor/README.md` 有入口。
