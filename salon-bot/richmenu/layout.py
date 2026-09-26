"""三個圖文選單的版面（圖片和按鈕範圍都從這裡產生，兩邊不會對不上）。

每一列是一個 list，每格 (標題, 小字, 顏色, 動作)；顏色：main=金色重點、in=綠、out=藍、None=灰
"""
W = 2500

MENUS = {
    "guest": (843, [
        [("申請成為員工", "店內員工請按這裡", "main", "apply")],
    ]),
    "staff": (1686, [
        [("上班打卡", "到店先按這裡", "in", "clock_in"),
         ("登記", "做完客人按這裡", "main", "log"),
         ("下班打卡", "下班按這裡看日報", "out", "clock_out")],
        [("今日紀錄", "看今天做了多少", None, "today"),
         ("本月統計", "看這個月累計", None, "month")],
    ]),
    "boss": (1686, [
        [("上班打卡", "到店先按這裡", "in", "clock_in"),
         ("登記", "做完客人按這裡", "main", "log"),
         ("下班打卡", "下班看日報", "out", "clock_out"),
         ("今日紀錄", "我今天的紀錄", None, "today")],
        [("我的本月", "我這個月累計", None, "month"),
         ("今日總表", "全店今天＋出勤", None, "shop_today"),
         ("本月總表", "全店本月統計", None, "shop_month"),
         ("員工管理", "審核 / 停用員工", None, "staff")],
    ]),
}


def cells(kind):
    """回傳 [(x, y, w, h, 標題, 小字, 顏色, 動作), ...]"""
    h, rows = MENUS[kind]
    rh = h // len(rows)
    out = []
    for r, row in enumerate(rows):
        cw = W // len(row)
        for c, (t, sub, color, act) in enumerate(row):
            w = W - cw * c if c == len(row) - 1 else cw   # 最後一格吃掉餘數
            out.append((c * cw, r * rh, w, rh, t, sub, color, act))
    return out
