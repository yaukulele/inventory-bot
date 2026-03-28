"""
初始庫存匯入腳本 — 3/27 庫存資料
執行方式：python init_data.py
"""
import sqlite3
import datetime
import os

DB_PATH = os.environ.get("DB_PATH", "inventory.db")


def now_str():
    return "2026-03-27 00:00:00"


def init_db(conn):
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


def insert_items(conn, brand, category, items):
    """items = [(model, quantity), ...]"""
    ts = now_str()
    for model, qty in items:
        try:
            conn.execute(
                "INSERT INTO inventory (brand, model, category, quantity, updated_at) VALUES (?,?,?,?,?)",
                (brand, model, category, qty, ts),
            )
            conn.execute(
                "INSERT INTO logs (model, action, amount, result_qty, operator, created_at) VALUES (?,?,?,?,?,?)",
                (model, "初始匯入", qty, qty, "init_data", ts),
            )
        except sqlite3.IntegrityError:
            print(f"  ⚠️ 跳過重複：{brand} / {model}")


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"🗑️ 已移除舊資料庫 {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    count = 0

    # ═══════════════════════════════════════════════════
    # Yamaha
    # ═══════════════════════════════════════════════════

    print("\n🏢 Yamaha")

    insert_items(conn, "Yamaha", "木吉他", [
        ("FSX400C", 4),
        ("FS400 BLK", 1),
        ("FS400 NS", 0),
        ("FS400C BLK", 3),
        ("FS400C NS", 3),
        ("F400 NS", 2),
        ("FG800", 0),
        ("FGX800C", 0),
        ("F310", 4),
        ("Storia II", 0),
        ("Storia I", 0),
        ("FS5", 1),
    ])
    print("  ✅ 木吉他 12 項")

    insert_items(conn, "Yamaha", "效果器/混音器", [
        ("AG03 B", 4),
        ("AG03 W", 5),
        ("AG06 B", 3),
        ("AG06 W", 2),
        ("AG08 B", 1),
        ("AG08 W", 0),
    ])
    print("  ✅ 效果器/混音器 6 項")

    insert_items(conn, "Yamaha", "電貝斯", [
        ("TRBX174 RM", 0),
        ("TRBX174 BL", 1),
        ("TRBX174 OVS", 0),
        ("TRBX304 BK", 0),
        ("TRBX304 RD", 1),
        ("TRBX304 BL", 0),
        ("TRBX304 GR", 0),
    ])
    print("  ✅ 電貝斯 7 項")

    insert_items(conn, "Yamaha", "電子琴", [
        ("E383", 3),
        ("E283", 8),
        ("E473", 0),
        ("NP-15 B", 0),
        ("NP-15 W", 0),
        ("NP-35 W", 0),
    ])
    print("  ✅ 電子琴 6 項")

    insert_items(conn, "Yamaha", "音箱", [
        ("THR10 II", 2),
        ("THR10II Wireless", 2),
        ("THR30 II WLBL", 0),
        ("THR30 II WLWH", 0),
        ("THR30 II WL奶油", 0),
    ])
    print("  ✅ Yamaha音箱 5 項")

    insert_items(conn, "Yamaha", "薩克斯風", [
        ("YDS-120", 0),
        ("YDS-150", 0),
        ("YAS-280", 1),
    ])
    print("  ✅ 薩克斯風 3 項")

    insert_items(conn, "Yamaha", "PA器材", [
        ("EAD10", 0),
        ("STAGEPAS 100BTR", 10),
        ("STAGEPAS 200BTR", 0),
        ("CASE-STP200", 0),
    ])
    print("  ✅ PA器材 4 項")

    insert_items(conn, "Yamaha", "鼓配件", [
        ("DS550U", 0),
        ("DFP9C", 2),
    ])
    print("  ✅ 鼓配件 2 項")

    insert_items(conn, "Yamaha", "靜音吉他", [
        ("SLG200S TBS", 1),
        ("SLG200S NT", 1),
    ])
    print("  ✅ 靜音吉他 2 項")

    # ════════════════════════════════════════════════════
    # D'Addario XS
    # ═══════════════════════════════════════════════════

    print("\n🏢 D'Addario XS")

    insert_items(conn, "D'Addario XS", "弦-AG", [
        ("XS AG 1047", 1),
        ("XS AG 1152", 8),
        ("XS AG 1253", 10),
        ("XS AG 1356", 5),
    ])
    print("  ✅ AG弦 4 項")

    insert_items(conn, "D'Addario XS", "弦-EG", [
        ("XS EG 0942", 4),
        ("XS EG 0946", 9),
        ("XS EG 1046", 2),
        ("XS EG 1052", 7),
        ("XS EG 1149", 11),
    ])
    print("  ✅ EG弦 5 項")

    # ═══════════════════════════════════════════════════
    # Veelah
    # ═══════════════════════════════════════════════════

    print("\n🏢 Veelah")

    insert_items(conn, "Veelah", "合板吉他", [
        ("VDMM", 0),
        ("VDSM", 0),
        ("VMCMM", 1),
        ("VGACMM", 1),
        ("VOMM", 1),
        ("VGACSM", 7),
        ("VMCSM", 1),
        ("VOSM", 0),
    ])
    print("  ✅ 合板吉他 8 項")

    insert_items(conn, "Veelah", "面單吉他", [
        ("V1 OMC", 1),
        ("V1 OMMC", 1),
        ("V1 OM", 1),
        ("V1 OMM", 1),
        ("V1 OM NAVY", 2),
        ("V1 OM Chapter 11", 0),
        ("V1 GA", 1),
        ("V1 GAC", 0),
        ("V1 GACM", 1),
        ("V1 GAC BLK", 0),
        ("V1 DMC", 0),
        ("V2 GAC", 1),
        ("V2 OM", 1),
        ("V3 GAC", 0),
    ])
    print("  ✅ 面單吉他 14 項")

    insert_items(conn, "Veelah", "全單吉他", [
        ("V7 SAS GAC", 0),
    ])
    print("  ✅ 全單吉他 1 項")

    insert_items(conn, "Veelah", "背帶", [
        ("Veelah背帶 黑", 6),
        ("Veelah背帶 粉", 7),
        ("Veelah背帶 藍", 6),
        ("Veelah背帶 卡其", 5),
        ("Veelah背帶 深綠", 5),
        ("Veelah背帶 淺綠", 7),
    ])
    print("  ✅ 背帶 6 項")

    # ═══════════════════════════════════════════════════
    # Singer
    # ═══════════════════════════════════════════════════

    print("\n🏢 Singer")

    insert_items(conn, "Singer", "吉他", [
        ("GA00 Maple", 1),
        ("GA00 Zebra", 1),
        ("GA00", 2),
        ("GA01", 2),
        ("GA01 BLK", 2),
        ("GA03", 2),
        ("D01", 0),
        ("D01 BLK", 0),
        ("P01", 1),
        ("P01 BLK", 2),
        ("GA04", 0),
    ])
    print("  ✅ Singer吉他 11 項")

    # ═══════════════════════════════════════════════════
    # 音箱（多品牌）
    # ═══════════════════════════════════════════════════

    print("\n🏢 音箱（多品牌）")

    insert_items(conn, "Fender", "音箱", [
        ("Champion II 25", 0),
        ("Rumble 15", 0),
        ("Rumble 25", 0),
        ("Frontman 20G", 0),
    ])
    print("  ✅ Fender音箱 4 項")

    insert_items(conn, "Marshall", "音箱", [
        ("MG10", 2),
        ("MG15G", 0),
        ("MG15R", 0),
        ("MG15GFX", 2),
    ])
    print("  ✅ Marshall音箱 4 項")

    insert_items(conn, "VOX", "音箱", [
        ("VMG10", 1),
        ("AC15C1", 1),
        ("MV50 AC", 3),
    ])
    print("  ✅ VOX音箱 3 項")

    insert_items(conn, "Mackie", "音箱", [
        ("CR3-X 白", 8),
    ])
    print("  ✅ Mackie 1 項")

    insert_items(conn, "BOSS", "效果器", [
        ("VE-22", 0),
    ])
    print("  ✅ BOSS 1 項")

    insert_items(conn, "Roland", "音箱", [
        ("PM-100", 3),
        ("Katana Go", 1),
    ])
    print("  ✅ Roland 2 項")

    insert_items(conn, "Ampeg", "音箱", [
        ("ROCKET BASS 104", 3),
        ("ROCKET BASS 112", 1),
    ])
    print("  ✅ Ampeg 2 項")

    # ═══════════════════════════════════════════════════
    # NUX
    # ═══════════════════════════════════════════════════

    print("\n🏢 NUX")

    insert_items(conn, "NUX", "效果器", [
        ("MG-101", 3),
        ("MG-30", 3),
        ("MG-400", 5),
        ("MG300 MKII", 5),
        ("Amp Academy Stomp", 2),
        ("NUX Solid Studio MKII", 1),
        ("ZEUS 電供", 1),
    ])
    print("  ✅ NUX效果器 7 項")

    insert_items(conn, "NUX", "音箱", [
        ("Mighty Space", 0),
        ("Mighty 8 BT MKll", 0),
        ("Mighty 20 MKll", 0),
        ("Mighty Bass 50BT", 0),
        ("Mighty lite BT MKII", 2),
        ("Mighty air", 2),
        ("NUX PA-50", 1),
        ("NUX AC-25", 0),
    ])
    print("  ✅ NUX音箱 8 項")

    insert_items(conn, "NUX", "錄音/直播", [
        ("MP-3 Mighty plug PRO", 4),
        ("MP-2 Mighty plug PRO", 6),
        ("C-5RC", 9),
        ("B-3 Plus", 2),
        ("B-10 Vlog", 3),
        ("B-6", 6),
        ("B-6 Pro", 2),
        ("B-7PSM", 7),
        ("C-9", 2),
    ])
    print("  ✅ NUX錄音/直播 9 項")

    insert_items(conn, "Cherub", "調音器", [
        ("WST-905 Li", 3),
        ("WST-915 Li", 5),
        ("WST-675 W", 52),
        ("WST-675 B", 11),
        ("WST-675 G", 13),
    ])
    print("  ✅ Cherub調音器 5 項")

    # ═══════════════════════════════════════════════════
    # Elixir
    # ═══════════════════════════════════════════════════

    print("\n🏢 Elixir")

    # 單包 AG
    insert_items(conn, "Elixir", "弦-AG單包", [
        ("EX AG PB 10-47", 43),
        ("EX AG PB 11-52", 32),
        ("EX AG PB 12-53", 14),
        ("EX AG PB 12-56", 10),
        ("EX AG Nano80/20 10-47", 44),
        ("EX AG Nano80/20 11-52", 25),
        ("EX AG Nano80/20 12-53", 11),
        ("EX AG Poly80/20 10-47", 68),
        ("EX AG Poly80/20 11-52", 62),
        ("EX AG Poly80/20 12-53", 81),
    ])
    print("  ✅ AG單包弦 10 項")

    # 單包 EG
    insert_items(conn, "Elixir", "弦-EG單包", [
        ("EX EG OPT 09-42", 15),
        ("EX EG OPT 09-46", 10),
        ("EX EG OPT 10-46", 25),
        ("EX EG OPT 10-52", 1),
        ("EX EG Nano 09-42", 23),
        ("EX EG Nano 09-46", 9),
        ("EX EG Nano 10-46", 36),
        ("EX EG Nano 10-52", 0),
        ("EX EG Poly 09-42", 11),
        ("EX EG Poly 09-46", 13),
        ("EX EG Poly 10-46", 0),
    ])
    print("  ✅ EG單包弦 11 項")

    # 單包 Bass
    insert_items(conn, "Elixir", "弦-Bass單包", [
        ("EX Bass Nano 45-100", 0),
        ("EX Bass Nano 45-105", 1),
    ])
    print("  ✅ Bass單包弦 2 項")

    # 三包裝
    insert_items(conn, "Elixir", "弦-三包裝", [
        ("EX 3pk AG PB 11-52", 5),
        ("EX 3pk AG PB 12-53", 0),
        ("EX 3pk AG Nano80/20 11-52", 6),
        ("EX 3pk AG Nano80/20 12-53", 9),
        ("EX 3pk EG Nano 09-42", 16),
        ("EX 3pk EG Nano 10-46", 26),
        ("EX 3pk EG OPT 09-42", 14),
        ("EX 3pk EG OPT 10-46", 8),
    ])
    print("  ✅ 三包裝弦 8 項")

    # 三包裝散
    insert_items(conn, "Elixir", "弦-三包裝散", [
        ("EX 3pk散 AG PB 11-52", 2),
        ("EX 3pk散 AG PB 12-53", 189),
        ("EX 3pk散 AG Nano80/20 11-52", 2),
        ("EX 3pk散 AG Nano80/20 12-53", 2),
        ("EX 3pk散 EG Nano 09-42", 0),
        ("EX 3pk散 EG Nano 10-46", 0),
        ("EX 3pk散 EG OPT 09-42", 0),
        ("EX 3pk散 EG OPT 10-46", 0),
    ])
    print("  ✅ 三包裝散弦 8 項")

    # ═══════════════════════════════════════════════════
    # aNueNue (aNN)
    # ══════════════════════════════════════════════════

    print("\n🏢 aNueNue")

    insert_items(conn, "aNueNue", "吉他", [
        ("M1", 1),
        ("M1E", 2),
        ("M2", 1),
        ("M2E", 1),
        ("M10", 1),
        ("M20", 1),
        ("M15", 2),
        ("M25", 2),
        ("MY10", 1),
        ("M32", 1),
        ("M52", 0),
        ("M77", 1),
        ("M60", 1),
        ("M88", 0),
        ("M100", 0),
        ("Clint", 0),
        ("BOB", 0),
        ("MTK PS", 1),
        ("MC10 AM", 1),
        ("MC10 LC", 1),
        ("MC10 GG", 1),
        ("MC10 BA", 2),
        ("MC10 BB", 2),
        ("MC10 BF", 2),
        ("MC10 IG", 1),
        ("L10", 3),
        ("L20", 1),
        ("L100", 0),
        ("LF28", 1),
        ("LF23", 1),
        ("MBS18E", 1),
        ("N520SP", 1),
        ("N520AC", 1),
    ])
    print("  ✅ aNueNue吉他 33 項")

    insert_items(conn, "aNueNue", "烏克麗麗", [
        ("US10 BB", 4),
        ("US10 LC", 4),
        ("US10 AM", 2),
        ("US10 BA", 3),
        ("UC10 BF", 2),
        ("UC10 IG", 3),
        ("UC10 BA", 2),
        ("UC10 QS", 2),
        ("UC10 AM", 4),
        ("UC10 LC", 5),
        ("UC10 BB", 3),
        ("B1", 3),
        ("B2", 2),
        ("B3", 3),
        ("K1", 1),
        ("K2", 1),
        ("K3", 0),
        ("U1", 3),
        ("U2", 3),
        ("U3", 2),
        ("S3", 3),
        ("S4", 1),
        ("C3", 3),
        ("C3E", 1),
        ("C4", 1),
        ("T3", 2),
        ("T4", 2),
        ("AC30", 2),
        ("AC60", 2),
        ("AT30", 2),
        ("AT60", 2),
        ("TM1E", 2),
        ("TM2", 1),
        ("TM2E", 2),
        ("TM3", 1),
        ("SS1E", 0),
        ("SS2", 2),
        ("SS2E", 4),
        ("Lyra-Dusty Rose", 1),
        ("Lyra-New White", 6),
        ("Lyra-Warm Gray", 2),
        ("Lyra-Cool Gray", 1),
        ("MTK SK", 1),
        ("LOUT", 1),
        ("AMM2", 0),
        ("AAA2", 2),
    ])
    print("  ✅ 烏克麗麗 46 項")

    insert_items(conn, "aNueNue", "拾音器&響孔蓋", [
        ("AG AirAir", 1),
        ("AG AB", 1),
        ("UK AB", 2),
        ("UK miniU", 3),
        ("SC84", 4),
        ("SC94", 8),
    ])
    print("  ✅ 拾音器&響孔蓋 6 項")

    insert_items(conn, "aNueNue", "鳥吉他背帶", [
        ("鳥背帶 紅", 6),
        ("鳥背帶 藍", 2),
        ("鳥背帶 橙", 4),
        ("鳥背帶 黃", 7),
        ("鳥背帶 綠", 5),
        ("鳥背帶 灰", 4),
        ("HBS-IL", 3),
        ("HBS-IN", 3),
        ("HBS-ID", 1),
    ])
    print("  ✅ 鳥吉他背帶 9 項")

    insert_items(conn, "aNueNue", "烏克背帶", [
        ("US1 紅", 4),
        ("US1 藍", 7),
        ("US1 橙", 4),
        ("US1 綠", 5),
        ("US1 黃", 5),
        ("US1 灰", 5),
    ])
    print("  ✅ 烏克背帶 6 項")

    insert_items(conn, "aNueNue", "掛勾背帶", [
        ("掛勾背帶 桃紅", 3),
        ("掛勾背帶 紅", 4),
        ("掛勾背帶 橘", 5),
        ("掛勾背帶 白", 4),
        ("掛勾背帶 灰", 4),
        ("掛勾背帶 黑", 4),
        ("掛勾背帶 棕", 3),
        ("掛勾背帶 藍", 3),
    ])
    print("  ✅ 掛勾背帶 8 項")

    insert_items(conn, "aNueNue", "弦", [
        ("紫極光弦 C/Tenor", 6),
        ("黑水弦 Tenor", 7),
        ("黑水弦 S/C", 9),
        ("清水弦 Tenor", 7),
        ("清水弦 S/C", 6),
        ("30寸尼龍弦", 2),
        ("藍月亮弦 S/C", 3),
        ("藍月亮弦 Tenor", 3),
        ("藍月亮弦 Tenor low G", 5),
        ("綠星球弦 S/C", 4),
        ("綠星球弦 Tenor", 5),
    ])
    print("  ✅ aNueNue弦 11 項")

    # ── 統計 ──
    conn.commit()
    cursor = conn.execute("SELECT COUNT(*) as cnt, SUM(quantity) as total FROM inventory")
    row = cursor.fetchone()
    print(f"\n{'═' * 40}")
    print(f"✅ 匯入完成！")

    brands = conn.execute("SELECT DISTINCT brand FROM inventory").fetchall()
    cats = conn.execute("SELECT DISTINCT category FROM inventory").fetchall()
    print(f"📊 共 {row[0]} 個型號 / {row[1]} 件庫存")
    print(f"🏢 {len(brands)} 個品牌：{', '.join(r[0] for r in brands)}")
    print(f"🏷️ {len(cats)} 個分類：{', '.join(r[0] for r in cats)}")

    conn.close()


if __name__ == "__main__":
    main()
