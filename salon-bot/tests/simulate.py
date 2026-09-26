"""不需要任何帳號就能跑的流程測試：python -m tests.simulate"""
import os
os.environ.update(STORE_BACKEND="memory", BOSS_CODE="1234")

from urllib.parse import parse_qs
from linebot.v3.messaging import PushMessageRequest, ReplyMessageRequest
from bot import config
from bot.logic import SalonBot
from bot.store import MemoryStore
from datetime import datetime

config.BOSS_CODE = "1234"


class FakeLine:
    def __init__(self):
        self.replies, self.pushes, self.menus = [], [], {}

    def reply(self, token, msgs):
        ReplyMessageRequest.from_dict({"replyToken": token, "messages": msgs})  # 確認格式合法
        assert 1 <= len(msgs) <= 5
        self.replies.append(msgs)

    def push(self, uid, msgs):
        PushMessageRequest.from_dict({"to": uid, "messages": msgs})
        self.pushes.append((uid, msgs))

    def link_menu(self, uid, kind): self.menus[uid] = kind
    def display_name(self, uid): return "媽媽"

    def last(self):
        m = self.replies[-1][0]
        return m.get("text") or m.get("altText")

    def last_actions(self):
        m = self.replies[-1][0]
        if "quickReply" in m:
            return [i["action"] for i in m["quickReply"]["items"]]
        if m["type"] == "flex":
            acts, stack = [], [m["contents"]]
            while stack:
                n = stack.pop()
                if isinstance(n, dict):
                    if n.get("type") == "button": acts.append(n["action"])
                    stack.extend(v for v in n.values() if isinstance(v, (dict, list)))
                elif isinstance(n, list): stack.extend(n)
            return acts
        return []

    def find(self, label):
        return next(a for a in self.last_actions() if a["label"].startswith(label))["data"]


clock = {"v": datetime(2026, 10, 5, 10, 55)}
def at(d, h, m): clock["v"] = datetime(2026, 10, d, h, m)
st, ln = MemoryStore(), FakeLine()
bot = SalonBot(st, ln, clock=lambda: clock["v"])
MOM, AMY, BEN, X = "Umom0000001", "Uamy0000002", "Uben0000003", "Ustranger4"

def show(tag): print(f"[{tag}]", ln.last().replace("\n", " | "))

# 1. 老闆綁定
bot.on_text(MOM, "#老闆 9999", "t"); show("錯密碼")
bot.on_text(MOM, "#老闆 1234", "t"); show("老闆綁定"); assert ln.menus[MOM] == "boss"

# 2. 員工申請
bot.on_follow(AMY, "t"); show("加好友")
bot.on_postback(AMY, "a=log", "t"); show("未開通按登記")
bot.on_postback(AMY, ln.find("申請"), "t"); show("按申請")
bot.on_text(AMY, "小美", "t"); show("輸入名字")
assert ln.pushes[-1][0] == MOM
bot.on_text(AMY, "哈囉", "t"); show("等待中亂打")

# 3. 非老闆不能核准
bot.on_follow(BEN, "t"); bot.on_postback(BEN, "a=apply", "t"); bot.on_text(BEN, "阿班", "t")
bot.on_postback(X, f"a=approve&u={AMY}", "t"); show("陌生人核准")

# 4. 老闆核准 / 拒絕
approve = next(a["data"] for a in ln.pushes[0][1][0]["contents"]["footer"]["contents"] and
               [b["action"] for b in ln.pushes[0][1][0]["contents"]["footer"]["contents"]] if a["label"] == "核准")
bot.on_postback(MOM, approve, "t"); show("核准小美"); assert ln.menus[AMY] == "staff"
bot.on_postback(MOM, approve, "t"); show("重複核准")
bot.on_postback(MOM, f"a=reject&u={BEN}", "t"); show("拒絕阿班")

# 5. 打卡：還沒上班不能下班
bot.on_postback(AMY, "a=clock_out", "t"); show("未上班按下班")
at(5, 11, 2); bot.on_postback(AMY, "a=clock_in", "t"); show("小美上班")
bot.on_postback(AMY, "a=clock_in", "t"); show("重複上班")

# 6. 登記流程（員工）
bot.on_postback(AMY, "a=log", "t"); assert len(ln.last_actions()) == 10
bot.on_postback(AMY, ln.find("男仕剪髮"), "t"); show("選項目")
cnt = ln.find("2 位")
bot.on_postback(AMY, cnt, "t"); show("選 2 位")
undo = ln.find("↩️")
bot.on_postback(AMY, cnt, "t"); show("重複按")
bot.on_postback(AMY, "a=log", "t"); bot.on_postback(AMY, ln.find("女仕染髮"), "t")
bot.on_postback(AMY, ln.find("1 位"), "t"); show("染髮 1 位")
bot.on_postback(AMY, undo, "t"); show("撤銷剪髮")
bot.on_postback(AMY, undo, "t"); show("再撤銷一次")
bot.on_postback(AMY, "a=log", "t"); bot.on_postback(AMY, ln.find("男仕剪髮"), "t"); bot.on_postback(AMY, ln.find("3 位"), "t")

# 7. 老闆自己也接客：登記、打卡、列入統計
bot.on_postback(MOM, "a=log", "t"); bot.on_postback(MOM, ln.find("快速護髮"), "t"); bot.on_postback(MOM, ln.find("2 位"), "t")
show("老闆沒打卡就登記"); assert "還沒打上班卡" in ln.last()
at(5, 11, 30); bot.on_postback(MOM, "a=clock_in", "t"); show("老闆上班")
bot.on_postback(MOM, "a=log", "t"); bot.on_postback(MOM, ln.find("女仕剪髮"), "t"); bot.on_postback(MOM, ln.find("1 位"), "t")
bot.on_postback(MOM, "a=today", "t"); show("老闆今日紀錄")
bot.on_postback(AMY, "a=shop_today", "t"); show("員工按總表")
bot.on_postback(MOM, "a=shop_today", "t"); print(ln.last())
assert "媽媽 E001" in ln.last() and "總計 7 人次" in ln.last()

# 8. 下班 → 日報
at(5, 20, 5)
n_push = len(ln.pushes)
bot.on_postback(AMY, "a=clock_out", "t"); show("按下班（確認卡）")
bot.on_postback(AMY, ln.find("確定下班"), "t"); print(ln.last())
assert len(ln.pushes) == n_push + 1 and ln.pushes[-1][0] == MOM
print("---- 推給老闆 ----"); print(ln.pushes[-1][1][0]["text"])
bot.on_postback(AMY, "a=clock_out_ok", "t"); show("重複確認下班")
bot.on_postback(AMY, "a=clock_in", "t"); show("下班後又按上班")
at(5, 20, 30); bot.on_postback(MOM, "a=clock_out_ok", "t"); show("老闆下班")
assert len(ln.pushes) == n_push + 1   # 老闆下班不推給自己

# 9. 跨日撤銷、月累計
at(6, 11, 0)
bot.on_postback(AMY, undo, "t")
bot.on_postback(AMY, "a=month", "t"); show("小美本月")

# 10. 員工管理 / 停用
bot.on_postback(MOM, "a=staff", "t"); show("員工管理")
bot.on_postback(MOM, ln.find("停用 小美"), "t"); show("停用"); assert ln.menus[AMY] == "guest"
bot.on_postback(AMY, "a=log", "t"); show("停用後按登記")
bot.on_postback(AMY, "a=apply", "t"); show("停用後申請")
bot.on_postback(MOM, "a=shop_month", "t"); print(ln.last())
print("\n全部測試通過 ✅")
