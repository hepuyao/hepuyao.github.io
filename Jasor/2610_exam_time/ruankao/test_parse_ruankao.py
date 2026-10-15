# Jasor/2610_exam_time/ruankao/test_parse_ruankao.py
from parse_ruankao import parseTaskOptions, parseCitySignup, pickReferenceBatchName

SAMPLE = """
<select name="taskid" id="taskid">
<option selected="selected" value="260710">2026年下半年软考</option>
<option value="260303">2026年上半年软考</option>
</select>
<div class="layui-row listCont selectorg"><div class="layui-col-md3 col1">北京</div><div class="layui-col-md4 col2 timeW">2026-09-11 00:00 ~ 2026-09-17 23:59</div><div class="layui-col-md4 col2 timeW">pay</div></div>
<div class="layui-row listCont selectorg"><div class="layui-col-md3 col1">天津</div><div class="layui-col-md4 col2 timeW">2026-08-27 09:00 ~ 2026-09-16 17:00</div></div>
"""

def test_parse_task_options_order_and_selected():
    tasks = parseTaskOptions(SAMPLE)
    assert tasks[0]["id"] == "260710"
    assert tasks[0]["name"] == "2026年下半年软考"
    assert tasks[0]["selected"] is True
    assert tasks[1]["name"] == "2026年上半年软考"

def test_parse_city_signup_beijing():
    row = parseCitySignup(SAMPLE, "北京")
    assert row["signupStart"] == "2026-09-11 00:00"
    assert row["signupEnd"] == "2026-09-17 23:59"

def test_parse_city_missing():
    assert parseCitySignup(SAMPLE, "上海") is None

def test_pick_reference_half():
    assert pickReferenceBatchName("2026年下半年软考") == "上半年"
    assert pickReferenceBatchName("2026年上半年软考") == "下半年"
