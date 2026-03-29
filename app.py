"""
æ¨¢å¨åº«å­ç®¡ç LINE Bot
==============================
æä½æåªéæåèï¼åç/åé¡å­å¨è³æåº«è£¡ã
åèå¦æéè¤ï¼ä¸ååçååèï¼ï¼ç³»çµ±æååºè®ä½ é¸ã

æä»¤èªªæï¼
  é²è²¨ FSX400C 5       â FSX400C é²è²¨ 5 ä»¶
  åºè²¨ AG03-B 2        â AG03-B åºè²¨ 2 ä»¶
  ç¤é» FSX400C 10      â æ ¡æ­£çº 10
  æ¥è©¢ FSX400C         â æ¥ç¹å®åè
  æ¥åç Yamaha        â ååºè©²åçææåº«å­
  æ¥åé¡ æ¨åä»         â ååºæ¨åä»ææåè
  åº«å­                  â å¨é¨åº«å­
  ç¼ºè²¨                  â ååºåº«å­ 0 çåå
  ç´é FSX400C         â æè¿ 10 ç­ç°å
  æ°å¢ åç åè åé¡ æ¸é â æ°å¢åå
  å¹«å©                  â é¡¯ç¤ºæä»¤
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
    PushMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.exceptions import InvalidSignatureError

# ââ è¨­å® ââââââââââââââââââââââââââââââââââââââââââââââ
app = Flask(__name__)

CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

DB_PATH = os.environ.get("DB_PATH", "inventory.db")


# ââ è³æåº« ââââââââââââââââââââââââââââââââââââââââââââ

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


# ââ æ¨¡ç³æå° âââââââââââââââââââââââââââââââââââââââââ

def find_model(conn, keyword: str):
    """ç²¾ç¢º â ä¸åå¤§å°å¯« â æ¨¡ç³åå«"""
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
    lines = ["ð æ¾å°å¤åç¸ç¬¦åèï¼è«è¼¸å¥å®æ´åèï¼"]
    for r in rows:
        lines.append(f"  {r['model']}ï¼{r['brand']} / {r['category']}ï¼åº«å­ {r['quantity']}")
    return "\n".join(lines)


# ââ åº«å­æä½ ââââââââââââââââââââââââââââââââââââââââââ

def stock_in(model: str, amount: int, operator: str = "") -> str:
    if amount <= 0:
        return "â ï¸ é²è²¨æ¸éå¿é å¤§æ¼ 0"
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
            return f"â æ¾ä¸å°ã{model}ãï¼è«åç¨ãæ°å¢ãæä»¤å»ºç«åå"
        conn.execute(
            "INSERT INTO logs (model, action, amount, result_qty, operator, created_at) VALUES (?,?,?,?,?,?)",
            (display, "é²è²¨", amount, new_qty, operator, now_str()),
        )
    return f"â é²è²¨æå\nð¦ {display} +{amount}\nð ç®ååº«å­ï¼{new_qty}"


def stock_out(model: str, amount: int, operator: str = "") -> str:
    if amount <= 0:
        return "â ï¸ åºè²¨æ¸éå¿é å¤§æ¼ 0"
    with get_db() as conn:
        found = find_model(conn, model)
        if isinstance(found, list):
            return format_multi_match(found)
        if not found:
            return f"â æ¾ä¸å°ã{model}ã"
        if found["quantity"] < amount:
            return f"â ï¸ åº«å­ä¸è¶³ï¼{found['model']} ç®ååªæ {found['quantity']} ä»¶"
        new_qty = found["quantity"] - amount
        conn.execute(
            "UPDATE inventory SET quantity = ?, updated_at = ? WHERE model = ?",
            (new_qty, now_str(), found["model"]),
        )
        conn.execute(
            "INSERT INTO logs (model, action, amount, result_qty, operator, created_at) VALUES (?,?,?,?,?,?)",
            (found["model"], "åºè²¨", amount, new_qty, operator, now_str()),
        )
    return f"â åºè²¨æå\nð¦ {found['model']} -{amount}\nð ç®ååº«å­ï¼{new_qty}"


def stock_adjust(model: str, amount: int, operator: str = "") -> str:
    if amount < 0:
        return "â ï¸ ç¤é»æ¸éä¸å¯çºè² æ¸"
    with get_db() as conn:
        found = find_model(conn, model)
        if isinstance(found, list):
            return format_multi_match(found)
        if not found:
            return f"â æ¾ä¸å°ã{model}ãï¼è«åç¨ãæ°å¢ãæä»¤å»ºç«åå"
        old_qty = found["quantity"]
        conn.execute(
            "UPDATE inventory SET quantity = ?, updated_at = ? WHERE model = ?",
            (amount, now_str(), found["model"]),
        )
        conn.execute(
            "INSERT INTO logs (model, action, amount, result_qty, operator, created_at) VALUES (?,?,?,?,?,?)",
            (found["model"], "ç¤é»", amount, amount, operator, now_str()),
        )
    diff = amount - old_qty
    sign = f"+{diff}" if diff >= 0 else str(diff)
    return f"â ç¤é»å®æ\nð¦ {found['model']} æ ¡æ­£çº {amount}ï¼{sign}ï¼"


def add_product(brand: str, model: str, category: str, quantity: int) -> str:
    """æ°å¢åå"""
    if quantity < 0:
        return "â ï¸ æ¸éä¸å¯çºè² æ¸"
    with get_db() as conn:
        existing = conn.execute("SELECT * FROM inventory WHERE model = ?", (model,)).fetchone()
        if existing:
            return f"â ï¸ ã{model}ãå·²å­å¨ï¼{existing['brand']} / {existing['category']}ï¼åº«å­ {existing['quantity']}"
        conn.execute(
            "INSERT INTO inventory (brand, model, category, quantity, updated_at) VALUES (?, ?, ?, ?, ?)",
            (brand, model, category, quantity, now_str()),
        )
        conn.execute(
            "INSERT INTO logs (model, action, amount, result_qty, operator, created_at) VALUES (?,?,?,?,?,?)",
            (model, "æ°å¢", quantity, quantity, "", now_str()),
        )
    return f"â æ°å¢æå\nð·ï¸ {brand} / {category}\nð¦ {model} åº«å­ï¼{quantity}"


def query_item(model: str) -> str:
    with get_db() as conn:
        found = find_model(conn, model)
        if isinstance(found, list):
            return format_multi_match(found)
        if not found:
            return f"ð æ¾ä¸å°ã{model}ã"
        return (
            f"ð¦ {found['model']}\n"
            f"ð·ï¸ {found['brand']} / {found['category']}\n"
            f"ð åº«å­ï¼{found['quantity']}\n"
            f"ð æ´æ°ï¼{found['updated_at']}"
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
            return f"ð æ¾ä¸å°åçã{brand}ã"

        total = sum(r["quantity"] for r in rows)
        in_stock = sum(1 for r in rows if r["quantity"] > 0)
        lines = [f"ð·ï¸ {brand}ï¼{in_stock}/{len(rows)} æåº«å­ï¼", "â" * 22]
        current_cat = None
        for r in rows:
            if r["category"] != current_cat:
                current_cat = r["category"]
                lines.append(f"\n  ã{current_cat}ã")
            mark = "  " if r["quantity"] > 0 else "â"
            lines.append(f"  {mark} {r['model']}ï¼{r['quantity']}")
        lines.append(f"\nåè¨ {total} ä»¶")
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
            cat_list = "ã".join(r["category"] for r in cats)
            return f"ð æ¾ä¸å°åé¡ã{category}ã\nð ç¾æåé¡ï¼{cat_list}"

        actual_cat = rows[0]["category"] if rows else category
        total = sum(r["quantity"] for r in rows)
        in_stock = sum(1 for r in rows if r["quantity"] > 0)
        lines = [f"ð·ï¸ {actual_cat}ï¼{in_stock}/{len(rows)} æåº«å­ï¼", "â" * 22]
        current_brand = None
        for r in rows:
            if r["brand"] != current_brand:
                current_brand = r["brand"]
                lines.append(f"\n  ã{current_brand}ã")
            mark = "  " if r["quantity"] > 0 else "â"
            lines.append(f"  {mark} {r['model']}ï¼{r['quantity']}")
        lines.append(f"\nåè¨ {total} ä»¶")
        return "\n".join(lines)


def list_all() -> str:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT brand, model, category, quantity FROM inventory ORDER BY brand, category, model"
        ).fetchall()
        if not rows:
            return "ð­ ç®åæ²æä»»ä½åº«å­è³æ"

        lines = ["ð åº«å­ç¸½è¦½", "â" * 22]
        current_brand = None
        current_cat = None
        total = 0
        in_stock_count = 0
        for r in rows:
            if r["brand"] != current_brand:
                current_brand = r["brand"]
                current_cat = None
                lines.append(f"\nð¢ {current_brand}")
            if r["category"] != current_cat:
                current_cat = r["category"]
                lines.append(f"  ã{current_cat}ã")
            mark = "  " if r["quantity"] > 0 else "â"
            lines.append(f"  {mark} {r['model']}ï¼{r['quantity']}")
            total += r["quantity"]
            if r["quantity"] > 0:
                in_stock_count += 1

        lines.append(f"\n{'â' * 22}")
        lines.append(f"å± {len(rows)} åè / {in_stock_count} æåº«å­ / åè¨ {total} ä»¶")
        return "\n".join(lines)


def list_low_stock(threshold: int = 0) -> str:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT brand, model, category, quantity FROM inventory WHERE quantity <= ? ORDER BY brand, category, model",
            (threshold,),
        ).fetchall()
        if not rows:
            return "â æ²æç¼ºè²¨ååï¼"
        lines = [f"â ï¸ {'ç¼ºè²¨' if threshold == 0 else f'ä½åº«å­ï¼âj$ {threshold}ï¼'}", "â" * 22]
        for r in rows:
            lines.append(f"  â {r['brand']} {r['model']}ï¼{r['category']}ï¼ï¼{r['quantity']}")
        lines.append(f"\nå± {len(rows)} é éè£è²¨")
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
            return f"ð­ ã{model}ãæ²æç°åç´é"
        lines = [f"ð {model} æè¿ç°å", "â" * 22]
        for r in rows:
            op = f"ï¼{r['operator'][:8]}ï¼" if r["operator"] else ""
            if r["action"] in ("ç¤é»", "æ°å¢"):
                lines.append(f"  {r['created_at']} {r['action']} â {r['result_qty']}{op}")
            else:
                lines.append(
                    f"  {r['created_at']} {r['action']} {r['amount']} â å© {r['result_qty']}{op}"
                )
        return "\n".join(lines)


HELP_TEXT = """ð åº«å­ç®¡çæä»¤èªªæ
ââââââââââââââââââ
é²è²¨ åè æ¸é
  ä¾ï¼é²è²¨ FSX400C 5
  ä¾ï¼é²è²¨ V1 OMC 3

åºè²¨ åè æ¸é
  ä¾ï¼åºè²¨ AG03-B 2

ç¤é» åè æ¸é
  ä¾ï¼ç¤é» FSX400C 10

æ¥è©¢ åè
  ä¾ï¼æ¥è©¢ V1 OMC

æ¥åç åç
  ä¾ï¼æ¥åç Yamaha

æ¥åé¡ åé¡å
  ä¾ï¼æ¥åé¡ æ¨åä»

åº«å­ â å¨é¨åº«å­

ç¼ºè²¨ â åº«å­ 0 çåå
ç¼ºè²¨ 3 â åº«å­ âj$ 3

ç´é åè
  ä¾ï¼ç´é FSX400C

æ°å¢ åç/åè/åé¡/æ¸é
  ä¾ï¼æ°å¢ Fender/Tele/é»åä»/3
  ä¾ï¼æ°å¢ Veelah/V1 OMC/é¢å®/2

å¹«å© â é¡¯ç¤ºæ­¤èªªæ

ð¡ åèæ¯æ´æ¨¡ç³æå°ï¼"""


# ââ è¨æ¯èç ââââââââââââââââââââââââââââââââââââââââââ

def _extract_model_and_amount(parts):
    """å¾ parts ä¸­ååºåèï¼å¯è½æç©ºæ ¼ï¼åæ¸éï¼æå¾ä¸åæ¸å­ï¼
    ä¾: ['V1', 'OMC', '5'] â ('V1 OMC', 5)
    ä¾: ['FSX400C', '5']  â ('FSX400C', 5)
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
    """å¾ parts ä¸­ååºåèï¼ææ parts åå¨ä¸èµ·ï¼
    ä¾: ['V1', 'OMC'] â 'V1 OMC'
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
    rest = parts[1:]  # æä»¤ä¹å¾çææå§å®¹

    if cmd in ("å¹«å©", "help", "èªªæ", "æä»¤"):
        return HELP_TEXT

    if cmd in ("åº«å­", "æ¸å®", "åè¡¨", "å¨é¨"):
        return list_all()

    if cmd in ("ç¼ºè²¨", "è£è²¨", "ä½åº«å­"):
        threshold = 0
        if rest:
            try:
                threshold = int(rest[0])
            except ValueError:
                pass
        return list_low_stock(threshold)

    if cmd in ("æ¥åç", "åç"):
        if not rest:
            return "â ï¸ æ ¼å¼ï¼æ¥åç åçå\nä¾ï¼æ¥åç Yamaha"
        return query_brand(rest[0])

    if cmd in ("æ¥åé¡", "åé¡"):
        if not rest:
            return "â ï¸ æ ¼å¼ï¼æ¥åé¡ åé¡å\nä¾ï¼æ¥åé¡ æ¨åä»"
        return query_category(" ".join(rest))

    # é²è²¨/åºè²¨/ç¤é»ï¼æå¾ä¸åæ¯æ¸éï¼ä¸­éå¨é¨æ¯åè
    if cmd in ("é²è²¨", "å¥åº«"):
        model, amount = _extract_model_and_amount(rest)
        if model is None:
            return "â ï¸ æ ¼å¼ï¼é²è²¨ åè æ¸é\nä¾ï¼é²è²¨ FSX400C 5\nä¾ï¼é²è²¨ V1 OMC 3"
        return stock_in(model, amount, user_name)

    if cmd in ("åºè²¨", "åºåº«"):
        model, amount = _extract_model_and_amount(rest)
        if model is None:
            return "â ï¸ æ ¼å¼ï¼åºè²¨ åè æ¸é\nä¾ï¼åºè²¨ AG03-B 2"
        return stock_out(model, amount, user_name)

    if cmd in ("ç¤é»", "æ ¡æ­£", "èª¿æ´"):
        model, amount = _extract_model_and_amount(rest)
        if model is None:
            return "â ï¸ æ ¼å¼ï¼ç¤é» åè æ¸é\nä¾ï¼ç¤é» FSX400C 10"
        return stock_adjust(model, amount, user_name)

    # æ¥è©¢/ç´éï¼æä»¤ä¹å¾å¨é¨é½æ¯åèå
    if cmd in ("æ¥è©¢", "æ¥", "ç"):
        model = _extract_model(rest)
        if not model:
            return "â ï¸ æ ¼å¼ï¼æ¥è©¢ åè\nä¾ï¼æ¥è©¢ FSX400C"
        return query_item(model)

    if cmd in ("ç´é", "è¨é", "æ­·å²", "log"):
        model = _extract_model(rest)
        if not model:
            return "â ï¸ æ ¼å¼ï¼ç´é åè\nä¾ï¼ç´é FSX400C"
        return query_logs(model)

    # æ°å¢ï¼æ°å¢ åç/åè/åé¡/æ¸éï¼ç¨ / åéï¼é¿åç©ºæ ¼åé¡ï¼
    if cmd in ("æ°å¢", "å»ºç«", "add"):
        joined = " ".join(rest)
        slash_parts = [p.strip() for p in joined.split("/")]
        if len(slash_parts) != 4:
            return "â ï¸ æ ¼å¼ï¼æ°å¢ åç/åè/åé¡/æ¸é\nä¾ï¼æ°å¢ Fender/Telecaster/é»åä»/3\nä¾ï¼æ°å¢ Veelah/V1 OMC/é¢å®åä»/2"
        brand, model, category = slash_parts[0], slash_parts[1], slash_parts[2]
        try:
            return add_product(brand, model, category, int(slash_parts[3]))
        except ValueError:
            return "â ï¸ æ¸éè«è¼¸å¥æ¸å­"

    return f"ð¤ ä¸èªè­ã{cmd}ã\nè¼¸å¥ãå¹«å©ãæ¥çæææä»¤"


# ââ LINE Webhook ââââââââââââââââââââââââââââââââââââââ

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    print(f"ð¨ Webhook received: {len(body)} bytes", flush=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("â Invalid signature", flush=True)
        abort(400)
    except Exception as e:
        print(f"â Callback error: {e}", flush=True)
        traceback.print_exc()
        sys.stdout.flush()
    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_text = event.message.text
    user_id = event.source.user_id if hasattr(event.source, "user_id") else ""
    print(f"ð¬ Message from {user_id[:8]}...: {user_text}", flush=True)
    reply = parse_and_execute(user_text, user_id)
    print(f"ð¤ Reply: {reply[:80]}...", flush=True)

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        # ååè©¦ replyï¼å¿«éåè¦ï¼åè²»ï¼
        try:
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply)],
                )
            )
            print("â Reply sent successfully", flush=True)
            return
        except Exception as e:
            print(f"â ï¸ Reply failed (token expired?): {e}", flush=True)

        # Reply å¤±æ â æ¹ç¨ Push Messageï¼åæ´ï¼
        if user_id:
            try:
                line_bot_api.push_message_with_http_info(
                    PushMessageRequest(
                        to=user_id,
                        messages=[TextMessage(text=reply)],
                    )
                )
                print("â Push message sent successfully", flush=True)
            except Exception as e2:
                print(f"â Push message also failed: {e2}", flush=True)
                traceback.print_exc()
                sys.stdout.flush()
        else:
            print("â No user_id available for push fallback", flush=True)


@app.route("/", methods=["GET"])
def health():
    return "ð¸ æ¨å¨åº«å­ç®¡çç³»çµ±éè¡ä¸­"


@app.route("/keep-alive", methods=["GET", "HEAD"])
def keep_alive():
    """ä¾å¤é¨ cron å®æå¼å«ï¼é²æ­¢ Render åè³ºæ¹æ¡ä¼ç """
    return "OK"


def auto_load_init_data():
    """ååææª¢æ¥ï¼è¥ inventory è¡¨çºç©ºï¼èªåå¯å¥åå§è³æ"""
    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
        if count == 0:
            try:
                from init_data import main as load_data
                load_data()
                print("â å·²èªåå¯å¥åå§åº«å­è³æ", flush=True)
            except Exception as e:
                print(f"â ï¸ èªåå¯å¥å¤±æï¼{e}", flush=True)
                traceback.print_exc()
        else:
            print(f"ð¦ è³æåº«å·²æ {count} ç­ååï¼è·³éå¯å¥", flush=True)


# ååæå·è¡åå§å
print("ð Starting inventory bot...", flush=True)
print(f"ð CHANNEL_SECRET set: {bool(CHANNEL_SECRET)}", flush=True)
print(f"ð CHANNEL_ACCESS_TOKEN set: {bool(CHANNEL_ACCESS_TOKEN)}", flush=True)
init_db()
auto_load_init_data()
print("â Bot ready!", flush=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
