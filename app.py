"""
樂器庫存管理 LINE Bot
==============================
操作時只需打型號，品牌/分類存在資料庫裡。
型號如有重複（不同品牌同型號），系統會列出讓你選。

指令說明：
  進貨 FSX400C 5       → FSX400C 進貨 5 件
  出貨 AG03-B 2        → AG03-B 出貨 2 件
  盤點 FSX400C 10      → 校正為 10
  查詢 FSX400C         → 查特定型號
  查品牌 Yamaha        → 列出該品牌所有庫存
  查分類 木吉他         → 列出木吉他所有型號
  庫存                  → 全部庫存
  缺貨                  → 列出庫存 0 的商品
  紀錄 FSX400C         → 最近 10 筆異動
  新增 品牌 型號 分類 數量 → 新增商品
  幫助                  → 顯示指令
"""

import os
import sys
import sqlite3
import datetime
import traceback
from contextlib import contextmanager

from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.exceptions import InvalidSignatureError

# ── 設定 ──────────────────────────────────────────────
app = Flask(__name__)

CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

DB_PATH = os.environ.get("DB_PATH", "inventory.db")


# ── 資料庫 ────────────────────────────────────────────

def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brand TEXT NOT NULL DEFAULT '',
                model TEXT UNIQUE NOT NULL,
                category TEXT NOT NULL DEFAULT '',
                quantity INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model TEXT NOT NULL,
                action TEXT NOT NULL,
                amount INTEGER NOT NULL,
                result_qty INTEGER NOT NULL,
                operator TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );
        """)


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def now_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ── 模糊搜尋 ─────────────────────────────────────────

def find_model(conn, keyword: str):
    """精確 → 不分大小寫 → 模糊包含"""
    row = conn.execute("SELECT * FROM inventory WHERE model = ?", (keyword,)).fetchone()
    if row:
        return row
    row = conn.execute(
        "SELECT * FROM inventory WHERE UPPER(model) = UPPER(?)", (keyword,)
    ).fetchone()
    if row:
        return row
    rows = conn.execute(
        "SELECT * FROM inventory WHERE UPPER(model) LIKE UPPER(?)",
        (f"%{keyword}%",),
    ).fetchall()
    if len(rows) == 1:
        return rows[0]
    if len(rows) > 1:
        return rows
    return None


def format_multi_match(rows):
    lines = ["🔍 找到多個相符型號，請輸入完整型號："]
    for r in rows:
        lines.append(f"  {r['model']}（{r['brand']} / {r['category']}）庫存 {r['quantity']}")
    return "\n".join(lines)


# ── 庫存操作 ──────────────────────────────────────────

def stock_in(model: str, amount: int, operator: str = "") -> str:
    if amount <= 0:
        return "⚠️ 進貨數量必須大於 0"
    with get_db() as conn:
        found = find_model(conn, model)
        if isinstance(found, list):
            return format_multi_match(found)
        if found:
            new_qty = found["quantity"] + amount
            conn.execute(
                "UPDATE inventory SET quantity = ?, updated_at = ? WHERE model = ?",
                (new_qty, now_str(), found["model"]),
            )
            display = found["model"]
        else:
            return f"❌ 找不到「{model}」，請先用「新增」指令建立商品"
        conn.execute(
            "INSERT INTO logs (model, action, amount, result_qty, operator, created_at) VALUES (?,?,?,?,?,?)",
            (display, "進貨", amount, new_qty, operator, now_str()),
        )
    return f"✅ 進貨成功\n📦 {display} +{amount}\n📊 目前庫存：{new_qty}"


def stock_out(model: str, amount: int, operator: str = "") -> str:
    if amount <= 0:
        return "⚠️ 出貨數量必須大於 0"
    with get_db() as conn:
        found = find_model(conn, model)
        if isinstance(found, list):
            return format_multi_match(found)
        if not found:
            return f"❌ 找不到「{model}」"
        if found["quantity"] < amount:
            return f"⚠️ 庫存不足！{found['model']} 目前只有 {found['quantity']} 件"
        new_qty = found["quantity"] - amount
        conn.execute(
            "UPDATE inventory SET quantity = ?, updated_at = ? WHERE model = ?",
            (new_qty, now_str(), found["model"]),
        )
        conn.execute(
            "INSERT INTO logs (model, action, amount, result_qty, operator, created_at) VALUES (?,?,?,?,?,?)",
            (found["model"], "出貨", amount, new_qty, operator, now_str()),
        )
    return f"✅ 出貨成功\n📦 {found['model']} -{amount}\n📊 目前庫存：{new_qty}"


def stock_adjust(model: str, amount: int, operator: str = "") -> str:
    if amount < 0:
        return "⚠️ 盤點數量不可為負數"
    with get_db() as conn:
        found = find_model(conn, model)
        if isinstance(found, list):
            return format_multi_match(found)
        if not found:
            return f"❌ 找不到「{model}」，請先用「新增」指令建立商品"
        old_qty = found["quantity"]
        conn.execute(
            "UPDATE inventory SET quantity = ?, updated_at = ? WHERE model = ?",
            (amount, now_str(), found["model"]),
        )
        conn.execute(
            "INSERT INTO logs (model, action, amount, result_qty, operator, created_at) VALUES (?,?,?,?,?,?)",
            (found["model"], "盤點", amount, amount, operator, now_str()),
        )
    diff = amount - old_qty
    sign = f"+{diff}" if diff >= 0 else str(diff)
    return f"✅ 盤點完成\n📦 {found['model']} 校正為 {amount}（{sign}）"


def add_product(brand: str, model: str, category: str, quantity: int) -> str:
    """新增商品"""
    if quantity < 0:
        return "⚠️ 數量不可為負數"
    with get_db() as conn:
        existing = conn.execute("SELECT * FROM inventory WHERE model = ?", (model,)).fetchone()
        if existing:
            return f"⚠️ 「{model}」已存在（{existing['brand']} / {existing['category']}）庫存 {existing['quantity']}"
        conn.execute(
            "INSERT INTO inventory (brand, model, category, quantity, updated_at) VALUES (?, ?, ?, ?, ?)",
            (brand, model, category, quantity, now_str()),
        )
        conn.execute(
            "INSERT INTO logs (model, action, amount, result_qty, operator, created_at) VALUES (?,?,?,?,?,?)",
            (model, "新增", quantity, quantity, "", now_str()),
        )
    return f"✅ 新增成功\n🏷️ {brand} / {category}\n📦 {model} 庫存：{quantity}"


def query_item(model: str) -> str:
    with get_db() as conn:
        found = find_model(conn, model)
        if isinstance(found, list):
            return format_multi_match(found)
        if not found:
            return f"🔍 找不到「{model}」"
        return (
            f"📦 {found['model']}\n"
            f"🏷️ {found['brand']} / {found['category']}\n"
            f"📊 庫存：{found['quantity']}\n"
            f"🕐 更新：{found['updated_at']}"
        )


def query_brand(brand: str) -> str:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT model, category, quantity FROM inventory WHERE brand = ? ORDER BY category, model",
            (brand,),
        ).fetchall()
        if not rows:
            rows = conn.execute(
                "SELECT model, category, quantity FROM inventory WHERE UPPER(brand) LIKE UPPER(?) ORDER BY category, model",
                (f"%{brand}%",),
            ).fetchall()
        if not rows:
            return f"🔍 找不到品牌「{brand}」"

        total = sum(r["quantity"] for r in rows)
        in_stock = sum(1 for r in rows if r["quantity"] > 0)
        lines = [f"🏷️ {brand}（{in_stock}/{len(rows)} 有庫存）", "─" * 22]
        current_cat = None
        for r in rows:
            if r["category"] != current_cat:
                current_cat = r["category"]
                lines.append(f"\n  【{current_cat}】")
            mark = "  " if r["quantity"] > 0 else "⛔"
            lines.append(f"  {mark} {r['model']}：{r['quantity']}")
        lines.append(f"\n合計 {total} 件")
        return "\n".join(lines)


def query_category(category: str) -> str:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT brand, model, category, quantity FROM inventory WHERE category = ? ORDER BY brand, model",
            (category,),
        ).fetchall()
        if not rows:
            rows = conn.execute(
                "SELECT brand, model, category, quantity FROM inventory WHERE category LIKE ? ORDER BY brand, model",
                (f"%{category}%",),
            ).fetchall()
        if not rows:
            cats = conn.execute("SELECT DISTINCT category FROM inventory ORDER BY category").fetchall()
            cat_list = "、".join(r["category"] for r in cats)
            return f"🔍 找不到分類「{category}」\n📋 現有分類：{cat_list}"

        actual_cat = rows[0]["category"] if rows else category
        total = sum(r["quantity"] for r in rows)
        in_stock = sum(1 for r in rows if r["quantity"] > 0)
        lines = [f"🏷️ {actual_cat}（{in_stock}/{len(rows)} 有庫存）", "─" * 22]
        current_brand = None
        for r in rows:
            if r["brand"] != current_brand:
                current_brand = r["brand"]
                lines.append(f"\n  【{current_brand}】")
            mark = "  " if r["quantity"] > 0 else "⛔"
            lines.append(f"  {mark} {r['model']}：{r['quantity']}")
        lines.append(f"\n合計 {total} 件")
        return "\n".join(lines)


def list_all() -> str:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT brand, model, category, quantity FROM inventory ORDER BY brand, category, model"
        ).fetchall()
        if not rows:
            return "📭 目前沒有任何庫存資料"

        lines = ["📋 庫存總覽", "═" * 22]
        current_brand = None
        current_cat = None
        total = 0
        in_stock_count = 0
        for r in rows:
            if r["brand"] != current_brand:
                current_brand = r["brand"]
                current_cat = None
                lines.append(f"\n🏢 {current_brand}")
            if r["category"] != current_cat:
                current_cat = r["category"]
                lines.append(f"  【{current_cat}】")
            mark = "  " if r["quantity"] > 0 else "⛔"
            lines.append(f"  {mark} {r['model']}：{r['quantity']}")
            total += r["quantity"]
            if r["quantity"] > 0:
                in_stock_count += 1

        lines.append(f"\n{'═' * 22}")
        lines.append(f"共 {len(rows)} 型號 / {in_stock_count} 有庫存 / 合計 {total} 件")
        return "\n".join(lines)


def list_low_stock(threshold: int = 0) -> str:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT brand, model, category, quantity FROM inventory WHERE quantity <= ? ORDER BY brand, category, model",
            (threshold,),
        ).fetchall()
        if not rows:
            return "✅ 沒有缺貨商品！"
        lines = [f"⚠️ {'缺貨' if threshold == 0 else f'低庫存（≤ {threshold}）'}", "─" * 22]
        for r in rows:
            lines.append(f"  ⛔ {r['brand']} {r['model']}（{r['category']}）：{r['quantity']}")
        lines.append(f"\n共 {len(rows)} 項需補貨")
        return "\n".join(lines)


def query_logs(model: str) -> str:
    with get_db() as conn:
        found = find_model(conn, model)
        if isinstance(found, list):
            return format_multi_match(found)
        if found:
            model = found["model"]
        rows = conn.execute(
            "SELECT * FROM logs WHERE model = ? ORDER BY id DESC LIMIT 10",
            (model,),
        ).fetchall()
        if not rows:
            return f"📭 「{model}」沒有異動紀錄"
        lines = [f"📜 {model} 最近異動", "─" * 22]
        for r in rows:
            op = f"（{r['operator'][:8]}）" if r["operator"] else ""
            if r["action"] in ("盤點", "新增"):
                lines.append(f"  {r['created_at']} {r['action']} → {r['result_qty']}{op}")
            else:
                lines.append(
                    f"  {r['created_at']} {r['action']} {r['amount']} → 剩 {r['result_qty']}{op}"
                )
        return "\n".join(lines)


HELP_TEXT = """📖 庫存管理指令說明
══════════════════
進貨 型號 數量
  例：進貨 FSX400C 5
  例：進貨 V1 OMC 3

出貨 型號 數量
  例：出貨 AG03-B 2

盤點 型號 數量
  例：盤點 FSX400C 10

查詢 型號
  例：查詢 V1 OMC

查品牌 品牌
  例：查品牌 Yamaha

查分類 分類名
  例：查分類 木吉他

庫存 → 全部庫存

缺貨 → 庫存 0 的商品
缺貨 3 → 庫存 ≤ 3

紀錄 型號
  例：紀錄 FSX400C

新增 品牌/型號/分類/數量
  例：新增 Fender/Tele/電吉他/3
  例：新增 Veelah/V1 OMC/面單/2

幫助 → 顯示此說明

💡 型號支援模糊搜尋！"""


# ── 訊息處理 ──────────────────────────────────────────

def _extract_model_and_amount(parts):
    """從 parts 中取出型號（可能有空格）和數量（最後一個數字）
    例: ['V1', 'OMC', '5'] → ('V1 OMC', 5)
    例: ['FSX400C', '5']  → ('FSX400C', 5)
    """
    if len(parts) < 2:
        return None, None
    try:
        amount = int(parts[-1])
        model = " ".join(parts[:-1])
        return model, amount
    except ValueError:
        return None, None


def _extract_model(parts):
    """從 parts 中取出型號（所有 parts 合在一起）
    例: ['V1', 'OMC'] → 'V1 OMC'
    """
    if not parts:
        return None
    return " ".join(parts)


def parse_and_execute(text: str, user_name: str = "") -> str:
    text = text.strip()
    parts = text.split()

    if not parts:
        return HELP_TEXT

    cmd = parts[0]
    rest = parts[1:]  # 指令之後的所有內容

    if cmd in ("幫助", "help", "說明", "指令"):
        return HELP_TEXT

    if cmd in ("庫存", "清單", "列表", "全部"):
        return list_all()

    if cmd in ("缺貨", "補貨", "低庫存"):
        threshold = 0
        if rest:
            try:
                threshold = int(rest[0])
            except ValueError:
                pass
        return list_low_stock(threshold)

    if cmd in ("查品牌", "品牌"):
        if not rest:
            return "⚠️ 格式：查品牌 品牌名\n例：查品牌 Yamaha"
        return query_brand(rest[0])

    if cmd in ("查分類", "分類"):
        if not rest:
            return "⚠️ 格式：查分類 分類名\n例：查分類 木吉他"
        return query_category(" ".join(rest))

    # 進貨/出貨/盤點：最後一個是數量，中間全部是型號
    if cmd in ("進貨", "入庫"):
        model, amount = _extract_model_and_amount(rest)
        if model is None:
            return "⚠️ 格式：進貨 型號 數量\n例：進貨 FSX400C 5\n例：進貨 V1 OMC 3"
        return stock_in(model, amount, user_name)

    if cmd in ("出貨", "出庫"):
        model, amount = _extract_model_and_amount(rest)
        if model is None:
            return "⚠️ 格式：出貨 型號 數量\n例：出貨 AG03-B 2"
        return stock_out(model, amount, user_name)

    if cmd in ("盤點", "校正", "調整"):
        model, amount = _extract_model_and_amount(rest)
        if model is None:
            return "⚠️ 格式：盤點 型號 數量\n例：盤點 FSX400C 10"
        return stock_adjust(model, amount, user_name)

    # 查詢/紀錄：指令之後全部都是型號名
    if cmd in ("查詢", "查", "看"):
        model = _extract_model(rest)
        if not model:
            return "⚠️ 格式：查詢 型號\n例：查詢 FSX400C"
        return query_item(model)

    if cmd in ("紀錄", "記錄", "歷史", "log"):
        model = _extract_model(rest)
        if not model:
            return "⚠️ 格式：紀錄 型號\n例：紀錄 FSX400C"
        return query_logs(model)

    # 新增：新增 品牌/型號/分類/數量（用 / 分隔，避免空格問題）
    if cmd in ("新增", "建立", "add"):
        joined = " ".join(rest)
        slash_parts = [p.strip() for p in joined.split("/")]
        if len(slash_parts) != 4:
            return "⚠️ 格式：新增 品牌/型號/分類/數量\n例：新增 Fender/Telecaster/電吉他/3\n例：新增 Veelah/V1 OMC/面單吉他/2"
        brand, model, category = slash_parts[0], slash_parts[1], slash_parts[2]
        try:
            return add_product(brand, model, category, int(slash_parts[3]))
        except ValueError:
            return "⚠️ 數量請輸入數字"

    return f"🤔 不認識「{cmd}」\n輸入「幫助」查看所有指令"


# ── LINE Webhook ──────────────────────────────────────

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    print(f"📨 Webhook received: {len(body)} bytes", flush=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("❌ Invalid signature", flush=True)
        abort(400)
    except Exception as e:
        print(f"❌ Callback error: {e}", flush=True)
        traceback.print_exc()
        sys.stdout.flush()
    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_text = event.message.text
    user_id = event.source.user_id if hasattr(event.source, "user_id") else ""
    print(f"💬 Message from {user_id[:8]}...: {user_text}", flush=True)
    reply = parse_and_execute(user_text, user_id)
    print(f"📤 Reply: {reply[:80]}...", flush=True)

    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply)],
                )
            )
        print("✅ Reply sent successfully", flush=True)
    except Exception as e:
        print(f"❌ Reply failed: {e}", flush=True)
        traceback.print_exc()
        sys.stdout.flush()


@app.route("/", methods=["GET"])
def health():
    return "🎸 樂器庫存管理系統運行中"


def auto_load_init_data():
    """啟動時檢查：若 inventory 表為空，自動匯入初始資料"""
    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
        if count == 0:
            try:
                from init_data import main as load_data
                load_data()
                print("✅ 已自動匯入初始庫存資料", flush=True)
            except Exception as e:
                print(f"⚠️ 自動匯入失敗：{e}", flush=True)
                traceback.print_exc()
        else:
            print(f"📦 資料庫已有 {count} 筆商品，跳過匯入", flush=True)


# 啟動時執行初始化
print("🚀 Starting inventory bot...", flush=True)
print(f"📋 CHANNEL_SECRET set: {bool(CHANNEL_SECRET)}", flush=True)
print(f"📋 CHANNEL_ACCESS_TOKEN set: {bool(CHANNEL_ACCESS_TOKEN)}", flush=True)
init_db()
auto_load_init_data()
print("✅ Bot ready!", flush=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
