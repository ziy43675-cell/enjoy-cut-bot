"""訊息長相都在這裡（LINE 的 JSON 格式），要改文字或排版改這個檔就好。"""
from urllib.parse import urlencode
from . import config


def pb(label, **data):
    """postback 按鈕動作。"""
    return {"type": "postback", "label": label, "data": urlencode(data), "displayText": label}


def text(t, quick=None):
    m = {"type": "text", "text": t}
    if quick:
        m["quickReply"] = {"items": [{"type": "action", "action": a} for a in quick[:13]]}
    return m


def buttons_card(title, body_lines, actions, color="#1F6FEB"):
    """一張卡片：標題 + 說明 + 一排按鈕。"""
    body = [{"type": "text", "text": l, "wrap": True, "size": "md"} for l in body_lines]
    btns = [{"type": "button", "style": "primary" if i == 0 else "secondary",
             "color": color if i == 0 else None, "height": "sm", "action": a}
            for i, a in enumerate(actions)]
    for b in btns:
        if b["color"] is None:
            del b["color"]
    return {"type": "flex", "altText": title, "contents": {
        "type": "bubble",
        "header": {"type": "box", "layout": "vertical", "contents": [
            {"type": "text", "text": title, "weight": "bold", "size": "lg"}]},
        "body": {"type": "box", "layout": "vertical", "spacing": "sm", "contents": body or [
            {"type": "filler"}]},
        "footer": {"type": "box", "layout": "vertical", "spacing": "sm", "contents": btns},
    }}


def item_picker(nonce):
    """十個項目按鈕，兩個一排。nonce 用來防止同一筆被重複登記。"""
    rows = []
    for i in range(0, len(config.ITEMS), 2):
        row = []
        for item_id, name in config.ITEMS[i:i + 2]:
            row.append({"type": "button", "style": "secondary", "height": "sm", "flex": 1,
                        "action": pb(name, a="item", i=item_id, t=nonce)})
        if len(row) == 1:
            row.append({"type": "filler", "flex": 1})
        rows.append({"type": "box", "layout": "horizontal", "spacing": "sm", "contents": row})
    return {"type": "flex", "altText": "請選擇項目", "contents": {
        "type": "bubble", "size": "mega",
        "header": {"type": "box", "layout": "vertical", "contents": [
            {"type": "text", "text": "✂️ 選擇項目", "weight": "bold", "size": "lg"}]},
        "body": {"type": "box", "layout": "vertical", "spacing": "sm", "contents": rows},
    }}


def count_picker(item_id, nonce):
    name = config.ITEM_NAME[item_id]
    quick = [pb(f"{n} 位", a="cnt", i=item_id, n=n, t=nonce)
             for n in range(1, config.MAX_COUNT_BUTTON + 1)]
    quick.append(pb("取消", a="cancel"))
    return text(f"「{name}」做了幾位？\n請點下方按鈕 👇", quick)


def after_log(item_name, count, today_total, rid):
    return text(
        f"✅ 已登記：{item_name} × {count} 位\n今天目前共 {today_total} 人次",
        [pb("➕ 繼續登記", a="log"), pb("↩️ 撤銷這筆", a="undo", r=rid)])


def approve_request(uid, name):
    return buttons_card("🙋 新員工申請", [f"姓名：{name}", "是否核准加入？"],
                        [pb("核准", a="approve", u=uid), pb("拒絕", a="reject", u=uid)])


def apply_prompt():
    return buttons_card("歡迎 👋", ["如果你是店內員工，請按下方按鈕申請，老闆核准後就能開始登記。"],
                        [pb("申請成為員工", a="apply")])
