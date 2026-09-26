"""Flask 入口。部署：gunicorn app:app"""
import logging
import threading
from flask import Flask, abort, request
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import FollowEvent, MessageEvent, PostbackEvent, TextMessageContent

from bot import config
from bot.line_client import LineClient
from bot.logic import SalonBot
from bot.store import make_store

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
handler = WebhookHandler(config.LINE_CHANNEL_SECRET)
bot = SalonBot(make_store(), LineClient(config.LINE_CHANNEL_ACCESS_TOKEN))


@app.get("/")
def health():
    # UptimeRobot 每 5 分鐘會打這裡，順便檢查要不要發每月 1 號的月結總表（背景執行，不拖慢回應）
    threading.Thread(target=_monthly, daemon=True).start()
    return "salon-bot ok"


def _monthly():
    try:
        bot.maybe_send_monthly_report()
    except Exception:
        logging.exception("月結推播失敗")


@app.post("/callback")
def callback():
    sig = request.headers.get("X-Line-Signature", "")
    try:
        handler.handle(request.get_data(as_text=True), sig)
    except InvalidSignatureError:
        abort(400)
    return "OK"


@handler.add(FollowEvent)
def _follow(e):
    bot.on_follow(e.source.user_id, e.reply_token)


@handler.add(MessageEvent, message=TextMessageContent)
def _text(e):
    if e.source.type == "user":            # 只處理一對一聊天，群組訊息不理
        bot.on_text(e.source.user_id, e.message.text, e.reply_token)


@handler.add(PostbackEvent)
def _postback(e):
    if e.source.type == "user":
        bot.on_postback(e.source.user_id, e.postback.data, e.reply_token)


if __name__ == "__main__":
    app.run(port=5000, debug=False)
