"""所有設定集中在這裡。帳號相關的值一律從環境變數讀取，換帳號不用改程式。"""
import os

# ── 營業項目（id 不要改，改 name 就好；新增項目往後加） ──
ITEMS = [
    ("m_cut",      "男仕剪髮"),
    ("f_cut",      "女仕剪髮"),
    ("buzz",       "平頭"),
    ("bangs",      "剪瀏海"),
    ("wash_addon", "洗髮(剪髮加購價)"),
    ("wash",       "一般洗髮"),
    ("f_dye",      "女仕染髮"),
    ("m_dye",      "男仕染髮"),
    ("scalp",      "染髮頭皮隔離"),
    ("treat",      "快速護髮"),
]
ITEM_NAME = dict(ITEMS)

MAX_COUNT_BUTTON = 10          # 人數按鈕 1~10
TZ = "Asia/Taipei"

# ── 環境變數 ──
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
FIREBASE_CREDENTIALS_JSON = os.getenv("FIREBASE_CREDENTIALS_JSON", "")  # 整份服務帳戶 JSON 內容
STORE_BACKEND = os.getenv("STORE_BACKEND", "firestore")   # firestore | memory（本機測試用）
BOSS_CODE = os.getenv("BOSS_CODE", "")                     # 老闆綁定密碼
# 員工按下班後，是否也推播一份他的日報給老闆（1=要、0=不要）
# 注意：推播會用到每月 200 則免費額度，員工多時可以關掉，老闆改用「今日總表」查看
NOTIFY_BOSS_ON_CLOCKOUT = os.getenv("NOTIFY_BOSS_ON_CLOCKOUT", "1") == "1"

# 每月 1 號自動推播上個月的月結總表給老闆（1=要、0=不要）
MONTHLY_REPORT = os.getenv("MONTHLY_REPORT", "1") == "1"
MONTHLY_REPORT_HOUR = int(os.getenv("MONTHLY_REPORT_HOUR", "9"))   # 1 號幾點以後發（台灣時間）

# 圖文選單名稱（setup_richmenu.py 建立時用同樣的名字，程式靠名字找 id）
MENU_GUEST = "salon-guest"
MENU_STAFF = "salon-staff"
MENU_BOSS = "salon-boss"
