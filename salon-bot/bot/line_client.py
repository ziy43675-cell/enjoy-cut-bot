"""包裝 LINE Messaging API（SDK v3）。"""
import logging
from linebot.v3.messaging import (ApiClient, Configuration, MessagingApi,
                                  PushMessageRequest, ReplyMessageRequest)
from . import config

log = logging.getLogger(__name__)
MENU_NAMES = {"guest": config.MENU_GUEST, "staff": config.MENU_STAFF, "boss": config.MENU_BOSS}


class LineClient:
    def __init__(self, access_token):
        self.conf = Configuration(access_token=access_token)
        self._menu_ids = {}

    def _api(self):
        return MessagingApi(ApiClient(self.conf))

    def reply(self, token, msgs):
        self._api().reply_message(ReplyMessageRequest.from_dict({"replyToken": token, "messages": msgs}))

    def push(self, uid, msgs):
        try:
            self._api().push_message(PushMessageRequest.from_dict({"to": uid, "messages": msgs}))
        except Exception:
            log.exception("push 失敗（可能是免費推播額度用完）")

    def display_name(self, uid):
        try:
            return self._api().get_profile(uid).display_name
        except Exception:
            return None

    def _menu_id(self, kind):
        name = MENU_NAMES[kind]
        if name not in self._menu_ids:
            for m in self._api().get_rich_menu_list().richmenus:
                self._menu_ids[m.name] = m.rich_menu_id
        return self._menu_ids.get(name)

    def link_menu(self, uid, kind):
        try:
            api = self._api()
            if kind == "guest":
                api.unlink_rich_menu_id_from_user(uid)   # 回到預設（訪客）選單
                return
            mid = self._menu_id(kind)
            if mid:
                api.link_rich_menu_id_to_user(uid, mid)
            else:
                log.warning("找不到圖文選單 %s，請先執行 setup_richmenu.py", kind)
        except Exception:
            log.exception("切換圖文選單失敗")
