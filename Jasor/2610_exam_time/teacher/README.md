# 天津教招（中学 / 教育系统）

静态页根据 `data.json` 展示最近教招公告，含物理岗与报名时间解析结果。

## 本地更新数据

```bash
cd Jasor/2610_exam_time/teacher
pip install -r requirements.txt
python3 fetch_teacher.py
python3 -m http.server 8765
```

打开 http://127.0.0.1:8765/

## 测试

```bash
python3 -m pytest test_parse_teacher.py -v
python3 -m py_compile parse_teacher.py fetch_teacher.py
```

## 自动更新

GitHub Actions 每天 UTC 03:00（约北京时间 11:00）抓取官网并提交 `data.json`。也可在 Actions 页手动 `workflow_dispatch`。
