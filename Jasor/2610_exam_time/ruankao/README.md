# 软考报名倒计时（北京 / 天津）

静态页根据 `data.json` 显示北京、天津报名窗口状态。

## 本地更新数据

```bash
cd Jasor/2610_exam_time/ruankao
python3 fetch_ruankao.py
python3 -m http.server 8765
```

打开 http://127.0.0.1:8765/

## 测试

```bash
python3 -m pytest test_parse_ruankao.py -v
node --test test_status.mjs
```

## 自动更新

GitHub Actions 每天 UTC 02:00（约北京时间 10:00）抓取官网并提交 `data.json`。也可在 Actions 页手动 `workflow_dispatch`。
