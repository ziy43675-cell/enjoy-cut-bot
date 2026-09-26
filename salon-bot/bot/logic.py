"""機器人的所有流程。不直接依賴 Flask 或 LINE SDK，方便本機測試。

line 物件需要提供：reply(token, msgs) / push(uid, msgs) / link_menu(uid, kind) / display_name(uid)
"""
import secrets
from datetime import datetime
from urllib.parse import parse_qs
from zoneinfo import ZoneInfo

from . import config, messages as M, reports

TZ = ZoneInfo(config.TZ)


def now():
    return datetime.now(TZ)


def _mins(hhmm):
    h, m = map(int, hhmm.split(":"))
    return h * 60 + m


class SalonBot:
    def __init__(self, store, line, clock=now):
        self.s, self.line, self.now = store, line, clock

    def today(self):
        return self.now().strftime("%Y-%m-%d")

    # ─────────── 事件入口 ───────────
    def on_follow(self, uid, token):
        u = self.s.get_user(uid)
        if u and u.get("status") == "active":
            self.line.link_menu(uid, u["role"])
            return self.line.reply(token, [M.text(f"歡迎回來，{u['name']}！請用下方選單操作 👇")])
        self.line.reply(token, [M.apply_prompt()])

    def on_text(self, uid, txt, token):
        txt = txt.strip()
        u = self.s.get_user(uid) or {}

        # 老闆綁定：傳「#老闆 密碼」
        if txt.startswith("#老闆"):
            return self._bind_boss(uid, u, txt[3:].strip(), token)

        # 等待輸入名字中
        if u.get("state") == "awaiting_name":
            return self._submit_name(uid, txt, token)

        if u.get("status") == "active":
            self.line.link_menu(uid, u["role"])      # 順便修復選單（重建選單後會掉）
            return self.line.reply(token, [M.text("請用下方選單的按鈕操作 👇",
                                                  [M.pb("➕ 登記", a="log"), M.pb("📋 今日紀錄", a="today")])])
        if u.get("status") == "pending":
            return self.line.reply(token, [M.text("你的申請已送出，正在等老闆核准，請稍等 🙏")])
        self.line.reply(token, [M.apply_prompt()])

    def on_postback(self, uid, data, token):
        d = {k: v[0] for k, v in parse_qs(data).items()}
        a = d.get("a")
        u = self.s.get_user(uid) or {}

        if a == "apply":
            return self._apply(uid, u, token)

        active = u.get("status") == "active"
        boss = active and u.get("role") == "boss"

        if a in ("approve", "reject", "shop_today", "shop_month", "staff", "disable", "pending"):
            if not boss:
                return self.line.reply(token, [M.text("這個功能只有老闆可以使用。")])
            return getattr(self, "_" + a)(uid, d, token)

        if not active:
            return self.line.reply(token, [M.apply_prompt()])

        if a == "clock_in":
            return self._clock_in(uid, u, token)
        if a == "clock_out":
            return self._clock_out_confirm(uid, u, token)
        if a == "clock_out_ok":
            return self._clock_out(uid, u, token)
        if a == "log":
            return self.line.reply(token, [M.item_picker(secrets.token_hex(6))])
        if a == "item":
            if d.get("i") not in config.ITEM_NAME:
                return self.line.reply(token, [M.text("這個項目已經不存在，請重新按「登記」。")])
            return self.line.reply(token, [M.count_picker(d["i"], d.get("t", ""))])
        if a == "cnt":
            return self._record(uid, u, d, token)
        if a == "undo":
            return self._undo(uid, d.get("r", ""), token)
        if a == "today":
            recs = self.s.records_by_user_date(uid, self.today())
            return self.line.reply(token, [M.text(reports.personal(
                recs, f"📋 {u['name']} 今日紀錄 {reports.fmt_date(self.today())}"),
                [M.pb("➕ 登記", a="log")])])
        if a == "month":
            month = self.today()[:7]
            recs = self.s.records_by_user_month(uid, month)
            days = sum(1 for x in self.s.attendance_by_month(month) if x.get("user_id") == uid)
            return self.line.reply(token, [M.text(reports.personal(
                recs, f"📅 {u['name']} {int(month[5:])}月累計") + f"\n本月出勤 {days} 天")])
        if a == "cancel":
            return self.line.reply(token, [M.text("已取消。")])
        self.line.reply(token, [M.text("看不懂這個指令，請用下方選單操作。")])

    # ─────────── 申請 / 綁定 ───────────
    def _apply(self, uid, u, token):
        if u.get("status") == "active":
            return self.line.reply(token, [M.text("你已經是員工了，可以直接登記 👍")])
        if u.get("status") == "pending":
            return self.line.reply(token, [M.text("你的申請正在等老闆核准，請稍等 🙏")])
        if u.get("status") == "disabled":
            return self.line.reply(token, [M.text("你的帳號已停用，如有問題請直接找老闆。")])
        self.s.save_user(uid, {"state": "awaiting_name"})
        self.line.reply(token, [M.text("請直接輸入你的名字（例如：小美）")])

    def _submit_name(self, uid, name, token):
        name = name[:10]
        if not name:
            return self.line.reply(token, [M.text("名字不能是空的，請再輸入一次。")])
        self.s.save_user(uid, {"name": name, "role": "staff", "status": "pending", "state": None})
        bosses = self.s.list_users(role="boss", status="active")
        for b in bosses:
            self.line.push(b["uid"], [M.approve_request(uid, name)])
        msg = f"已送出申請：{name}\n老闆核准後會通知你 🙏"
        if not bosses:
            msg += "\n（系統還沒有設定老闆帳號，請先通知老闆）"
        self.line.reply(token, [M.text(msg)])

    def _bind_boss(self, uid, u, code, token):
        if not config.BOSS_CODE or code != config.BOSS_CODE:
            return self.line.reply(token, [M.text("密碼錯誤。")])
        name = u.get("name") or self.line.display_name(uid) or "老闆"
        data = {"role": "boss", "status": "active", "name": name, "state": None}
        if not u.get("emp_no"):
            data["emp_no"] = self.s.next_emp_no()
        self.s.save_user(uid, data)
        self.line.link_menu(uid, "boss")
        self.line.reply(token, [M.text(f"✅ 已設定為老闆帳號：{name}（{data.get('emp_no', u.get('emp_no'))}）\n"
                                       "下方選單已切換為老闆版。")])

    # ─────────── 登記 ───────────
    def _record(self, uid, u, d, token):
        iid, nonce = d.get("i"), d.get("t", "")
        try:
            n = int(d.get("n", "0"))
        except ValueError:
            n = 0
        if iid not in config.ITEM_NAME or not (1 <= n <= 99) or not nonce:
            return self.line.reply(token, [M.text("資料有誤，請重新按「登記」。")])
        day = self.today()
        rid = f"{uid[-8:]}-{nonce}"
        ok = self.s.add_record(rid, {
            "user_id": uid, "name": u["name"], "emp_no": u.get("emp_no", ""),
            "item_id": iid, "item_name": config.ITEM_NAME[iid], "count": n,
            "date": day, "month": day[:7]})
        if not ok:
            return self.line.reply(token, [M.text("這筆已經登記過了，不會重複計算 👍",
                                                  [M.pb("➕ 登記新的一筆", a="log")])])
        total = sum(r["count"] for r in self.s.records_by_user_date(uid, day))
        msg = M.after_log(config.ITEM_NAME[iid], n, total, rid)
        if not self.s.get_attendance(uid, day):
            msg["text"] += "\n\n⚠️ 提醒：今天還沒打上班卡"
            msg["quickReply"]["items"].insert(0, {"type": "action", "action": M.pb("☀️ 上班打卡", a="clock_in")})
        self.line.reply(token, [msg])

    def _undo(self, uid, rid, token):
        r = self.s.get_record(rid)
        if not r or r["user_id"] != uid:
            return self.line.reply(token, [M.text("找不到這筆紀錄。")])
        if r.get("voided"):
            return self.line.reply(token, [M.text("這筆已經撤銷過了。")])
        if r["date"] != self.today():
            return self.line.reply(token, [M.text("只能撤銷今天的紀錄，之前的請找老闆修改。")])
        self.s.void_record(rid)
        self.line.reply(token, [M.text(f"↩️ 已撤銷：{r['item_name']} × {r['count']} 位",
                                       [M.pb("➕ 重新登記", a="log")])])

    # ─────────── 老闆功能 ───────────
    def _approve(self, uid, d, token):
        target = d.get("u", "")
        t = self.s.get_user(target)
        if not t or t.get("status") != "pending":
            st = {"active": "已經核准過了", "rejected": "已經拒絕過了"}.get((t or {}).get("status"), "找不到這筆申請")
            return self.line.reply(token, [M.text(st + "。")])
        no = t.get("emp_no") or self.s.next_emp_no()
        self.s.save_user(target, {"status": "active", "role": "staff", "emp_no": no})
        self.line.link_menu(target, "staff")
        self.line.push(target, [M.text(f"🎉 {t['name']}，你的帳號已開通（編號 {no}）\n"
                                       "之後做完客人，按下方選單的「登記」就可以了！")])
        self.line.reply(token, [M.text(f"✅ 已核准：{t['name']}（{no}）")])

    def _reject(self, uid, d, token):
        target = d.get("u", "")
        t = self.s.get_user(target)
        if not t or t.get("status") != "pending":
            return self.line.reply(token, [M.text("這筆申請已經處理過了。")])
        self.s.save_user(target, {"status": "rejected"})
        self.line.reply(token, [M.text(f"已拒絕：{t['name']}")])

    def _pending(self, uid, d, token):
        ps = self.s.list_users(status="pending")
        if not ps:
            return self.line.reply(token, [M.text("目前沒有待審核的申請。")])
        self.line.reply(token, [M.approve_request(p["uid"], p["name"]) for p in ps[:5]])

    def _staff(self, uid, d, token):
        us = [x for x in self.s.list_users(status="active")]
        us.sort(key=lambda x: x.get("emp_no", ""))
        lines = [f"{x.get('emp_no', '')} {x['name']}{'（老闆）' if x['role'] == 'boss' else ''}" for x in us]
        staff = [x for x in us if x["role"] == "staff"]
        quick = [M.pb(f"停用 {x['name']}"[:20], a="disable", u=x["uid"]) for x in staff[:11]]
        quick.insert(0, M.pb("待審核申請", a="pending"))
        self.line.reply(token, [M.text("👥 目前員工\n\n" + "\n".join(lines) +
                                       "\n\n要停用員工，點下方按鈕。", quick)])

    def _disable(self, uid, d, token):
        target = d.get("u", "")
        t = self.s.get_user(target)
        if not t or t.get("role") != "staff" or t.get("status") != "active":
            return self.line.reply(token, [M.text("找不到這位在職員工。")])
        self.s.save_user(target, {"status": "disabled"})
        self.line.link_menu(target, "guest")
        self.line.reply(token, [M.text(f"已停用：{t['name']}（過去的紀錄都會保留）")])

    def _shop_today(self, uid, d, token):
        day = self.today()
        self.line.reply(token, [M.text(reports.shop(self.s.records_by_date(day),
                                                    f"📊 今日總表 {reports.fmt_date(day)}",
                                                    attendance=self.s.attendance_by_date(day)))])

    def _shop_month(self, uid, d, token):
        month = self.today()[:7]
        self.line.reply(token, [M.text(reports.shop(self.s.records_by_month(month),
                                                    f"📅 {month[:4]}年{int(month[5:])}月 全店累計",
                                                    month_attendance=self.s.attendance_by_month(month)))])

    # ─────────── 打卡 ───────────
    def _clock_in(self, uid, u, token):
        day, t = self.today(), self.now().strftime("%H:%M")
        a = self.s.get_attendance(uid, day)
        if a and a.get("clock_out"):
            return self.line.reply(token, [M.text(
                f"你今天已經下班了（{a['clock_in']}–{a['clock_out']}）。\n如果要重新上班，請找老闆處理。")])
        if a:
            return self.line.reply(token, [M.text(f"你今天 {a['clock_in']} 已經打過上班卡了 👍",
                                                  [M.pb("➕ 登記", a="log")])])
        self.s.save_attendance(uid, day, {"user_id": uid, "name": u["name"], "emp_no": u.get("emp_no", ""),
                                          "date": day, "month": day[:7], "clock_in": t, "clock_out": None})
        self.line.reply(token, [M.text(f"☀️ 上班打卡成功\n{u['name']}　{reports.fmt_date(day)} {t}\n今天加油！",
                                       [M.pb("➕ 登記", a="log")])])

    def _clock_out_confirm(self, uid, u, token):
        day = self.today()
        a = self.s.get_attendance(uid, day)
        if not a:
            return self.line.reply(token, [M.text("你今天還沒打上班卡，不能下班喔。",
                                                  [M.pb("☀️ 上班打卡", a="clock_in")])])
        if a.get("clock_out"):
            return self.line.reply(token, [M.text(f"你今天 {a['clock_out']} 已經下班了。",
                                                  [M.pb("📋 今日紀錄", a="today")])])
        total = sum(r["count"] for r in self.s.records_by_user_date(uid, day))
        self.line.reply(token, [M.buttons_card(
            "確定要下班了嗎？",
            [f"上班時間：{a['clock_in']}", f"今天已登記：{total} 人次", "確認後會產生今日日報。"],
            [M.pb("確定下班", a="clock_out_ok"), M.pb("還沒，繼續登記", a="log")])])

    def _clock_out(self, uid, u, token):
        day, t = self.today(), self.now().strftime("%H:%M")
        a = self.s.get_attendance(uid, day)
        if not a:
            return self.line.reply(token, [M.text("你今天還沒打上班卡。", [M.pb("☀️ 上班打卡", a="clock_in")])])
        if a.get("clock_out"):   # 重複按確認
            return self.line.reply(token, [M.text(f"你今天 {a['clock_out']} 已經下班了。")])
        self.s.save_attendance(uid, day, {"clock_out": t})
        mins = max(0, _mins(t) - _mins(a["clock_in"]))
        report = reports.personal(self.s.records_by_user_date(uid, day),
                                  f"📋 {u['name']} 今日日報 {reports.fmt_date(day)}")
        head = (f"🌙 下班打卡成功 {t}\n上班 {a['clock_in']} ～ 下班 {t}"
                f"（{mins // 60} 小時 {mins % 60} 分）\n辛苦了！\n\n")
        self.line.reply(token, [M.text(head + report)])

        if config.NOTIFY_BOSS_ON_CLOCKOUT and u.get("role") != "boss":
            note = M.text(f"🌙 {u['name']} 已下班（{a['clock_in']}–{t}）\n\n" + report)
            for b in self.s.list_users(role="boss", status="active"):
                self.line.push(b["uid"], [note])
