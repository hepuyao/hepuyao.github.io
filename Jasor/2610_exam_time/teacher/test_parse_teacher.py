from parse_teacher import (
    matchTitle,
    extractPhysicsFromText,
    extractSignupFromText,
    extractPhysicsFromSheetRows,
    parseWebListGgLinks,
    extractSignupFromTimeList,
)


def test_match_title_education_system():
    hits = matchTitle("2026年红桥区教育系统公开招聘高层次人才")
    assert "教育系统" in hits


def test_match_title_zhongxue():
    assert "中学" in matchTitle("天津市第七中学2026年公开招聘高层次教育人才")


def test_skip_kindergarten_only():
    assert matchTitle("某某幼儿园公开招聘教师") == []


def test_physics_from_html_text():
    text = "招聘岗位包括中学物理教师、中学语文教师"
    result = extractPhysicsFromText(text)
    assert result["found"] is True
    assert any("物理" in (p.get("name") or "") for p in result["posts"])


def test_physics_absent():
    assert extractPhysicsFromText("招聘中学语文教师、数学教师")["found"] is False


def test_physics_from_sheet_row():
    rows = [
        ["单位", "岗位", "人数", "其它"],
        ["第七中学", "中学物理教师（专技岗）", "1", "初级中学及以上教师资格"],
    ]
    result = extractPhysicsFromSheetRows(rows)
    assert result["found"] is True
    assert "物理" in result["posts"][0]["name"]


def test_sheet_ignores_physical_chemistry_major_only():
    rows = [
        [
            "化学教师",
            "1",
            "研究生：物理化学（070304）、有机化学；本科：化学",
            "具有高中化学教师资格证书",
        ]
    ]
    assert extractPhysicsFromSheetRows(rows)["found"] is False


def test_heping_style_physics_teacher_row():
    rows = [
        [
            "天津市和平区教育局所属中学",
            "物理教师 （专技岗十二级及以下）",
            "中学",
            "从事物理教育、教学工作",
            "1",
            "1.具有高中学段物理教师资格证",
        ]
    ]
    result = extractPhysicsFromSheetRows(rows)
    assert result["found"] is True
    assert "物理教师" in result["posts"][0]["name"]


def test_signup_range():
    text = "网上报名时间：2026年8月4日9:00至2026年8月8日17:00，逾期不再受理。"
    result = extractSignupFromText(text)
    assert result["found"] is True
    assert result["raw"]
    assert "2026" in (result["raw"] or "")


def test_signup_absent():
    assert extractSignupFromText("考核方式为试讲和答辩")["found"] is False


def test_signup_nav_word_only_not_signup():
    assert extractSignupFromText("报名 办事指南 首页 联系我们")["found"] is False


def test_parse_weblist_gg_links():
    html = (
        "<div onclick=\"win_open('WebPage.aspx?id=abc')\">公告</div>"
        "<div onclick=\"win_open('https://zxbm.tjtalents.com.cn/wsbm_ggfb/attached/file/a.xls')\">计划表</div>"
    )
    links = parseWebListGgLinks(html)
    assert links["sheets"][0].endswith(".xls")
    assert "WebPage.aspx?id=abc" in links["pages"][0]


def test_extract_signup_from_timeline():
    sjx = (
        "[{ name: '报名时间',kdate: '2026年8月27日 14:00', zdate: '2026年9月3日 14:00', "
        "state: '已完成', infourl: '', remark: '' }]"
    )
    result = extractSignupFromTimeList(sjx)
    assert result["found"] is True
    assert result["start"] == "2026-08-27T14:00+08:00"
    assert result["end"] == "2026-09-03T14:00+08:00"
