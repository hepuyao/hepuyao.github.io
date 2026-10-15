# Jasor 工具入口

这里提供浏览器工具入口：

- <a href="/Jasor/2604_erp_to_plm/app.html" target="_blank" rel="noopener noreferrer">ERP → PLM 转换</a>
- <a href="/Jasor/2604_plm_check_table/app.html" target="_blank" rel="noopener noreferrer">PLM 表检测（B/AA）</a>
- <a href="/Jasor/2608_clipboard/" target="_blank" rel="noopener noreferrer">剪切板历史查看</a>
- <a href="/Jasor/2608_notebook_vague/" target="_blank" rel="noopener noreferrer">模糊笔记</a>
- <a href="/Jasor/2610_exam_time/ruankao/" target="_blank" rel="noopener noreferrer">软考报名倒计时（北京 / 天津）</a>
- <a href="/Jasor/2610_exam_time/teacher/" target="_blank" rel="noopener noreferrer">天津教招（中学 / 教育系统）</a>
- 桌面透明窗：`2608_notebook_tran_desktop/`（本地 `python3 app.py`）

## 功能说明

- ERP → PLM 转换：读取 ERP 输入表，按既定规则转换并下载 PLM 文件。
- PLM 表检测（B/AA）：比较检测表与总数据（文件夹或单文件），检查 B 列重复并校验 AA 列是否一致。
- notebook vague：网页 vague pad；本机 `note_backend.py` 同步；桌面窗见 `2608_notebook_tran_desktop/`。
- 软考报名倒计时：读取 `data.json`，展示北京、天津报名未开始 / 进行中 / 大约还剩等状态；数据由 GitHub Actions 日更。
- 天津教招：读取 `data.json`，展示最近教招标题、物理岗与报名时间；数据由 GitHub Actions 日更。
