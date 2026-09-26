"""建立三個圖文選單並設定訪客版為預設。換 LINE 帳號後要重跑一次。

用法：
    export LINE_CHANNEL_ACCESS_TOKEN=xxxx
    python setup_richmenu.py
"""
import os
import sys
from urllib.parse import urlencode

from linebot.v3.messaging import (ApiClient, Configuration, MessagingApi,
                                  MessagingApiBlob, RichMenuRequest)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "richmenu"))
from bot import config  # noqa: E402
from layout import MENUS as LAYOUT, cells  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def areas(kind):
    return [{"bounds": {"x": x, "y": y, "width": w, "height": h},
             "action": {"type": "postback", "label": t, "data": urlencode({"a": act}), "displayText": t}}
            for x, y, w, h, t, _, _, act in cells(kind)]


NAMES = {"guest": config.MENU_GUEST, "staff": config.MENU_STAFF, "boss": config.MENU_BOSS}
BAR = {"guest": "申請", "staff": "選單", "boss": "選單"}
MENUS = [(NAMES[k], f"{k}.png", LAYOUT[k][0], BAR[k], areas(k)) for k in LAYOUT]


def main():
    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
    if not token:
        sys.exit("請先設定 LINE_CHANNEL_ACCESS_TOKEN")
    client = ApiClient(Configuration(access_token=token))
    api, blob = MessagingApi(client), MessagingApiBlob(client)

    # 刪掉同名的舊選單，確保可以重複執行
    names = {m[0] for m in MENUS}
    for m in api.get_rich_menu_list().richmenus:
        if m.name in names:
            api.delete_rich_menu(m.rich_menu_id)
            print("刪除舊選單", m.name)

    ids = {}
    for name, img, h, bar, areas in MENUS:
        req = RichMenuRequest.from_dict({"size": {"width": 2500, "height": h}, "selected": True,
                                         "name": name, "chatBarText": bar, "areas": areas})
        rid = api.create_rich_menu(req).rich_menu_id
        with open(os.path.join(HERE, "richmenu", img), "rb") as f:
            blob.set_rich_menu_image(rid, body=bytearray(f.read()), _headers={"Content-Type": "image/png"})
        ids[name] = rid
        print("建立", name, rid)

    api.set_default_rich_menu(ids[config.MENU_GUEST])
    print("完成！訪客選單已設為預設。已核准的員工/老闆會在下次核准或綁定時自動切換。")
    print("如果是重建選單，老闆請重新傳一次「#老闆 密碼」，員工的選單可由老闆在後台重新核准。")


if __name__ == "__main__":
    main()
