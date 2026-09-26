"""把紀錄整理成文字報表。"""
from collections import OrderedDict, defaultdict
from datetime import date as _date
from . import config

WEEK = "一二三四五六日"


def fmt_date(d):
    y, m, dd = map(int, d.split("-"))
    return f"{m}/{dd}（{WEEK[_date(y, m, dd).weekday()]}）"


def _item_lines(counter):
    """依照 ITEMS 的順序列出有數字的項目。"""
    lines = [f"・{name} {counter[iid]}" for iid, name in config.ITEMS if counter.get(iid)]
    # 已從清單移除的舊項目也要算進去
    known = set(config.ITEM_NAME)
    for iid, n in counter.items():
        if iid not in known and n:
            lines.append(f"・{iid} {n}")
    return lines


def _sum_items(records):
    c = defaultdict(int)
    for r in records:
        c[r["item_id"]] += r["count"]
    return c


def personal(records, title):
    if not records:
        return f"{title}\n\n目前還沒有紀錄。"
    c = _sum_items(records)
    return "\n".join([title, "", *_item_lines(c), "", f"合計 {sum(c.values())} 人次"])


def _attendance_lines(attendance):
    lines = []
    for a in sorted(attendance, key=lambda a: a.get("emp_no", "")):
        out = a.get("clock_out") or "上班中"
        lines.append(f"・{a['name']} {a['clock_in']}–{out}")
    return lines


def _month_attendance_lines(att):
    days = defaultdict(int)
    names = {}
    for a in att:
        days[a.get("emp_no", "")] += 1
        names[a.get("emp_no", "")] = a["name"]
    return [f"・{names[no]} {days[no]} 天" for no in sorted(days)]


def shop(records, title, attendance=None, month_attendance=None):
    """全店報表：出勤 + 每位員工一段，最後全店合計。"""
    head = [title]
    if attendance:
        head += ["", "【出勤】", *_attendance_lines(attendance)]
    if month_attendance:
        head += ["", "【出勤天數】", *_month_attendance_lines(month_attendance)]
    if not records:
        return "\n".join(head + ["", "沒有任何登記紀錄。"])
    by_emp = OrderedDict()
    for r in sorted(records, key=lambda r: r.get("emp_no", "")):
        by_emp.setdefault((r.get("emp_no", ""), r.get("name", "")), []).append(r)
    parts = head
    for (no, name), recs in by_emp.items():
        c = _sum_items(recs)
        parts += ["", f"【{name} {no}】", *_item_lines(c), f"小計 {sum(c.values())} 人次"]
    total = _sum_items(records)
    parts += ["", "━━━━━━━━", "【全店合計】", *_item_lines(total), f"總計 {sum(total.values())} 人次"]
    return "\n".join(parts)
