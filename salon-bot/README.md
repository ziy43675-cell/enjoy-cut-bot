# 美髮店 LINE 登記機器人（v1）

員工和老闆都用 LINE 按鈕打卡、登記做了哪些項目和幾位，按下班就產生當天日報。全程按鈕操作，不用打指令。

## 功能

| 身分 | 可以做的事 |
|---|---|
| 訪客（剛加好友） | 申請成為員工（輸入一次名字） |
| 員工 | 上班打卡、登記（選項目 → 選人數）、撤銷今天的紀錄、下班打卡（產生個人日報）、今日紀錄、本月累計＋出勤天數 |
| 老闆 | 跟員工一樣可以打卡、登記自己的客人（列入全店統計）＋ 今日總表（含出勤）、本月總表（含出勤天數）、核准/拒絕申請、停用員工 |

- 員工編號自動產生（E001、E002…），停用員工後舊紀錄保留。
- 同一筆按兩次不會重複計算。
- 員工只能撤銷「今天」自己的紀錄。
- 下班要按確認，避免誤按；員工下班後老闆會收到他的日報（`NOTIFY_BOSS_ON_CLOCKOUT=0` 可關掉，省推播額度）。
- 沒打上班卡就登記，會提醒去打卡；沒打上班卡不能下班。
- 每人每天一次上下班，下班後要重新上班請老闆處理（下一版後台可改）。
- 月統計每月自動歸零重算，舊月份資料保留；月報下方有「◀ 看上個月」按鈕可以往回查。
- 每月 1 號 9 點後，自動推播上個月的月結總表給老闆（由 UptimeRobot 每 5 分鐘戳 `/` 時順便檢查，每月只發一次；`MONTHLY_REPORT=0` 關閉、`MONTHLY_REPORT_HOUR` 改時間）。

## 專案結構

```
app.py               Flask 入口（/callback 給 LINE）
bot/config.py        營業項目清單、環境變數  ← 要改項目改這裡
bot/logic.py         所有流程
bot/messages.py      訊息/按鈕長相
bot/reports.py       報表文字
bot/store.py         Firestore / 記憶體 兩種資料庫
bot/line_client.py   LINE API 包裝
setup_richmenu.py    建立圖文選單（換帳號後跑一次）
richmenu/layout.py   選單版面（按鈕位置、文字）
richmenu/*.png       選單圖片（make_images.py 依 layout 重新產生）
tests/simulate.py    不需任何帳號的完整流程測試
```

## 現在就能做（不用任何帳號）

```bash
pip install -r requirements.txt
python -m tests.simulate
```

會模擬：老闆綁定 → 員工申請 → 核准 → 上班打卡 → 登記 → 重複按 → 撤銷 → 老闆登記 → 總表 → 下班日報 → 停用，全部跑過會顯示「全部測試通過」。

## 用自己的帳號做測試版（建議先做）

1. 用你自己的 LINE 到 LINE Developers 開一個測試用 Messaging API channel，Firebase 開一個測試專案。
2. 照 `.env.example` 填好環境變數，部署到 Railway（或本機 + ngrok）。
3. `python setup_richmenu.py` 建立圖文選單。
4. LINE Developers 把 Webhook URL 設成 `https://你的網域/callback`，開啟 Use webhook。
5. 用手機加好友 → 傳 `#老闆 你的密碼` → 用另一支手機/家人帳號測員工流程。

## 換成弟弟的正式帳號

程式完全不用改，只要：

1. Railway 環境變數換成正式的 `LINE_CHANNEL_SECRET`、`LINE_CHANNEL_ACCESS_TOKEN`、`FIREBASE_CREDENTIALS_JSON`。
2. 用正式 token 跑一次 `python setup_richmenu.py`。
3. 正式 channel 的 Webhook URL 指到 Railway 網址 `/callback`。
4. 媽媽加好友，傳 `#老闆 密碼`，完成。

## 部署注意

- 官方帳號後台要：關閉「自動回應訊息」、開啟「Webhook」、關閉「加入好友的歡迎訊息」（機器人自己會回）。
- 時區固定台灣時間。

## 修改營業項目

改 `bot/config.py` 的 `ITEMS`：
- 改名字：只改右邊中文，id 不要動（舊紀錄靠 id 對應）。
- 新增：往清單後面加一行，id 用英文不要重複。
- 項目最多建議 12 個以內，手機上按鈕才不會太擠。

## 下一版預計

- 管理後台網頁：月報表（跟紙本一樣的格式）、切換單一員工、匯出 Excel、線上改項目
- 補登前幾天的紀錄
- 支出登記
- 抽成／業績計算
- 老闆後台修改打卡時間
