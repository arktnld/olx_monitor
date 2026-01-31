import sqlite3
import json
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

DB_PATH = Path(__file__).parent.parent / "data" / "olx.db"


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS searches (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE,
                base_url TEXT,
                queries TEXT,
                categories TEXT,
                exclude_keywords TEXT,
                active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ads (
                id INTEGER PRIMARY KEY,
                url TEXT UNIQUE,
                title TEXT,
                price TEXT,
                description TEXT,
                state TEXT,
                municipality TEXT,
                neighbourhood TEXT,
                zipcode TEXT,
                seller TEXT,
                condition TEXT,
                published_at TEXT,
                main_category TEXT,
                sub_category TEXT,
                hobbie_type TEXT,
                images TEXT,
                olx_pay BOOLEAN DEFAULT 0,
                olx_delivery BOOLEAN DEFAULT 0,
                search_id INTEGER,
                found_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                seen BOOLEAN DEFAULT 0,
                watching BOOLEAN DEFAULT 0,
                status TEXT DEFAULT 'active',
                deactivated_at DATETIME,
                FOREIGN KEY (search_id) REFERENCES searches(id)
            )
        """)

        # Migration: add status columns if not exist
        cursor.execute("PRAGMA table_info(ads)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'status' not in columns:
            cursor.execute("ALTER TABLE ads ADD COLUMN status TEXT DEFAULT 'active'")
        if 'deactivated_at' not in columns:
            cursor.execute("ALTER TABLE ads ADD COLUMN deactivated_at DATETIME")

        # Migration: add location/category columns to searches if not exist
        cursor.execute("PRAGMA table_info(searches)")
        search_columns = [col[1] for col in cursor.fetchall()]
        if 'state' not in search_columns:
            cursor.execute("ALTER TABLE searches ADD COLUMN state TEXT DEFAULT ''")
        if 'region' not in search_columns:
            cursor.execute("ALTER TABLE searches ADD COLUMN region TEXT DEFAULT ''")
        if 'category' not in search_columns:
            cursor.execute("ALTER TABLE searches ADD COLUMN category TEXT DEFAULT 'games'")
        if 'subcategory' not in search_columns:
            cursor.execute("ALTER TABLE searches ADD COLUMN subcategory TEXT DEFAULT ''")
        if 'cheap_threshold' not in search_columns:
            cursor.execute("ALTER TABLE searches ADD COLUMN cheap_threshold REAL")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY,
                ad_id INTEGER,
                price TEXT,
                checked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ad_id) REFERENCES ads(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_alerts (
                id INTEGER PRIMARY KEY,
                ad_id INTEGER UNIQUE,
                target_price REAL,
                notify_below BOOLEAN DEFAULT 1,
                active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                triggered_at DATETIME,
                FOREIGN KEY (ad_id) REFERENCES ads(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS push_subscriptions (
                id INTEGER PRIMARY KEY,
                endpoint TEXT UNIQUE,
                p256dh TEXT,
                auth TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for better query performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ads_search_id ON ads(search_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ads_status ON ads(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ads_watching ON ads(watching)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ads_found_at ON ads(found_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ads_status_found ON ads(status, found_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ads_watching_found ON ads(watching, found_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_history_ad ON price_history(ad_id, checked_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_searches_active ON searches(active)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_alerts_active ON price_alerts(active, ad_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_push_subscriptions_endpoint ON push_subscriptions(endpoint)")

        conn.commit()


# ==================== SETTINGS ====================

def get_setting(key: str, default: str = None) -> Optional[str]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row['value'] if row else default


def set_setting(key: str, value: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = ?
        """, (key, value, value))
        conn.commit()


# ==================== SEARCHES ====================

def get_all_searches():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM searches ORDER BY name")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_active_searches():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM searches WHERE active = 1 ORDER BY name")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_search_by_id(search_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM searches WHERE id = ?", (search_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def create_search(name: str, base_url: str, queries: list, categories: list, exclude_keywords: list,
                  state: str = '', region: str = '', category: str = 'games', subcategory: str = '',
                  cheap_threshold: float = None):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO searches (name, base_url, queries, categories, exclude_keywords, state, region, category, subcategory, cheap_threshold)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, base_url, json.dumps(queries), json.dumps(categories), json.dumps(exclude_keywords),
              state, region, category, subcategory, cheap_threshold))
        conn.commit()
        return cursor.lastrowid


def update_search(search_id: int, name: str, base_url: str, queries: list, categories: list, exclude_keywords: list, active: bool,
                  state: str = '', region: str = '', category: str = 'games', subcategory: str = '',
                  cheap_threshold: float = None):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE searches
            SET name = ?, base_url = ?, queries = ?, categories = ?, exclude_keywords = ?, active = ?,
                state = ?, region = ?, category = ?, subcategory = ?, cheap_threshold = ?
            WHERE id = ?
        """, (name, base_url, json.dumps(queries), json.dumps(categories), json.dumps(exclude_keywords), active,
              state, region, category, subcategory, cheap_threshold, search_id))
        conn.commit()


def delete_search(search_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM searches WHERE id = ?", (search_id,))
        conn.commit()


def toggle_search_active(search_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE searches SET active = NOT active WHERE id = ?", (search_id,))
        conn.commit()


# ==================== ADS ====================

def _build_ads_filter(search_id=None, status="all", min_price=None, max_price=None,
                      state=None, days=None, ad_status=None, search_text=None):
    """Helper para construir filtros de ads (reduz duplicação)"""
    conditions = []
    params = []

    if search_id:
        conditions.append("search_id = ?")
        params.append(search_id)

    if search_text:
        conditions.append("(LOWER(title) LIKE ? OR LOWER(description) LIKE ?)")
        search_pattern = f"%{search_text.lower()}%"
        params.extend([search_pattern, search_pattern])

    status_map = {"new": "seen = 0", "seen": "seen = 1", "watching": "watching = 1"}
    if status in status_map:
        conditions.append(status_map[status])

    if ad_status:
        conditions.append("status = ?")
        params.append(ad_status)

    price_cast = "CAST(REPLACE(REPLACE(price, '.', ''), ',', '.') AS REAL)"
    if min_price is not None:
        conditions.append(f"{price_cast} >= ?")
        params.append(min_price)

    if max_price is not None:
        conditions.append(f"{price_cast} <= ?")
        params.append(max_price)

    if state:
        conditions.append("state = ?")
        params.append(state)

    if days:
        conditions.append("found_at >= datetime('now', ?)")
        params.append(f"-{days} days")

    where = " AND ".join(conditions) if conditions else "1=1"
    return where, params


def get_ads(search_id: Optional[int] = None, status: str = "all",
            min_price: Optional[float] = None, max_price: Optional[float] = None,
            state: Optional[str] = None, days: Optional[int] = None,
            ad_status: Optional[str] = None, search_text: Optional[str] = None,
            sort_by: Optional[str] = None,
            limit: int = 100, offset: int = 0):

    where, params = _build_ads_filter(search_id, status, min_price, max_price,
                                       state, days, ad_status, search_text)

    sort_map = {
        'price_asc': "CAST(REPLACE(REPLACE(price, '.', ''), ',', '.') AS REAL) ASC",
        'price_desc': "CAST(REPLACE(REPLACE(price, '.', ''), ',', '.') AS REAL) DESC",
    }
    order = sort_map.get(sort_by, "found_at DESC")

    query = f"SELECT * FROM ads WHERE {where} ORDER BY {order} LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def get_ad_by_id(ad_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ads WHERE id = ?", (ad_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_ad_by_url(url: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ads WHERE url = ?", (url,))
        row = cursor.fetchone()
        return dict(row) if row else None


def ad_exists(url: str) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM ads WHERE url = ?", (url,))
        return cursor.fetchone() is not None


def get_existing_urls(urls: list[str]) -> set[str]:
    """Batch check which URLs already exist in database"""
    if not urls:
        return set()
    with get_connection() as conn:
        cursor = conn.cursor()
        placeholders = ','.join('?' * len(urls))
        cursor.execute(f"SELECT url FROM ads WHERE url IN ({placeholders})", urls)
        return {row['url'] for row in cursor.fetchall()}


def create_ad(url: str, title: str, price: str, description: str, state: str,
              municipality: str, neighbourhood: str, zipcode: str, seller: str,
              condition: str, published_at: str, main_category: str, sub_category: str,
              hobbie_type: str, images: list, olx_pay: bool, olx_delivery: bool,
              search_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ads (url, title, price, description, state, municipality,
                           neighbourhood, zipcode, seller, condition, published_at,
                           main_category, sub_category, hobbie_type, images,
                           olx_pay, olx_delivery, search_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (url, title, price, description, state, municipality, neighbourhood,
              zipcode, seller, condition, published_at, main_category, sub_category,
              hobbie_type, json.dumps(images), olx_pay, olx_delivery, search_id))
        conn.commit()
        return cursor.lastrowid


def mark_ad_seen(ad_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE ads SET seen = 1 WHERE id = ?", (ad_id,))
        conn.commit()


def toggle_ad_watching(ad_id: int) -> bool:
    """
    Toggle watching status. Returns True if now watching, False if stopped.
    Downloads images when starting to watch.
    """
    from services.images import download_ad_images

    with get_connection() as conn:
        cursor = conn.cursor()

        # Pegar estado atual e imagens
        cursor.execute("SELECT watching, images FROM ads WHERE id = ?", (ad_id,))
        row = cursor.fetchone()
        if not row:
            return False

        was_watching = bool(row['watching'])
        now_watching = not was_watching

        # Atualizar no banco
        cursor.execute("UPDATE ads SET watching = ? WHERE id = ?", (now_watching, ad_id))
        conn.commit()

        # Se começou a acompanhar, baixar imagens
        if now_watching and row['images']:
            try:
                images = json.loads(row['images']) if isinstance(row['images'], str) else row['images']
                if images:
                    download_ad_images(ad_id, images)
            except Exception as e:
                print(f"Erro ao baixar imagens do anúncio {ad_id}: {e}")

        return now_watching


def get_watching_ads(min_price=None, max_price=None, state=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM ads WHERE watching = 1"
        params = []

        if min_price is not None:
            query += " AND CAST(REPLACE(REPLACE(price, '.', ''), ',', '.') AS REAL) >= ?"
            params.append(min_price)

        if max_price is not None:
            query += " AND CAST(REPLACE(REPLACE(price, '.', ''), ',', '.') AS REAL) <= ?"
            params.append(max_price)

        if state:
            query += " AND state = ?"
            params.append(state)

        query += " ORDER BY found_at DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def update_ad_price(ad_id: int, new_price: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE ads SET price = ? WHERE id = ?", (new_price, ad_id))
        conn.commit()


def update_ad_status(ad_id: int, status: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        if status == 'inactive':
            cursor.execute(
                "UPDATE ads SET status = ?, deactivated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, ad_id)
            )
        else:
            cursor.execute(
                "UPDATE ads SET status = ?, deactivated_at = NULL WHERE id = ?",
                (status, ad_id)
            )
        conn.commit()


def get_ads_to_check():
    """Get active ads to check their status"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, url FROM ads
            WHERE status = 'active'
            ORDER BY found_at DESC
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_inactive_ads(min_price=None, max_price=None, state=None, search_text=None):
    """Get inactive/expired ads for history page"""
    with get_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM ads WHERE status = 'inactive'"
        params = []

        if search_text:
            query += " AND (LOWER(title) LIKE ? OR LOWER(description) LIKE ?)"
            search_pattern = f"%{search_text.lower()}%"
            params.extend([search_pattern, search_pattern])

        if min_price is not None:
            query += " AND CAST(REPLACE(REPLACE(price, '.', ''), ',', '.') AS REAL) >= ?"
            params.append(min_price)

        if max_price is not None:
            query += " AND CAST(REPLACE(REPLACE(price, '.', ''), ',', '.') AS REAL) <= ?"
            params.append(max_price)

        if state:
            query += " AND state = ?"
            params.append(state)

        query += " ORDER BY deactivated_at DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_ads_count_by_search():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT search_id, COUNT(*) as count
            FROM ads
            WHERE seen = 0 AND status = 'active'
            GROUP BY search_id
        """)
        rows = cursor.fetchall()
        return {row['search_id']: row['count'] for row in rows}


def get_ads_count(search_id: Optional[int] = None, status: str = "all",
                  min_price: Optional[float] = None, max_price: Optional[float] = None,
                  state: Optional[str] = None, days: Optional[int] = None,
                  ad_status: Optional[str] = None, search_text: Optional[str] = None):
    """Conta o total de anúncios com os filtros aplicados"""
    where, params = _build_ads_filter(search_id, status, min_price, max_price,
                                       state, days, ad_status, search_text)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) as count FROM ads WHERE {where}", params)
        return cursor.fetchone()['count']


def get_distinct_states():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT state FROM ads WHERE state IS NOT NULL AND state != '' ORDER BY state")
        return [row['state'] for row in cursor.fetchall()]


# ==================== PRICE HISTORY ====================

def add_price_history(ad_id: int, price: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO price_history (ad_id, price)
            VALUES (?, ?)
        """, (ad_id, price))
        conn.commit()


def get_price_history(ad_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM price_history
            WHERE ad_id = ?
            ORDER BY checked_at ASC
        """, (ad_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_last_price_check(ad_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM price_history
            WHERE ad_id = ?
            ORDER BY checked_at DESC
            LIMIT 1
        """, (ad_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


# ==================== PRICE ALERTS ====================

def create_price_alert(ad_id: int, target_price: float, notify_below: bool = True) -> int:
    """Create or update a price alert for an ad"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO price_alerts (ad_id, target_price, notify_below, active)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(ad_id) DO UPDATE SET
                target_price = excluded.target_price,
                notify_below = excluded.notify_below,
                active = 1,
                triggered_at = NULL
        """, (ad_id, target_price, notify_below))
        conn.commit()
        return cursor.lastrowid


def get_price_alert(ad_id: int):
    """Get price alert for an ad"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM price_alerts WHERE ad_id = ?
        """, (ad_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_active_price_alerts():
    """Get all active price alerts with ad info"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT pa.*, a.title, a.price, a.url, a.images
            FROM price_alerts pa
            JOIN ads a ON pa.ad_id = a.id
            WHERE pa.active = 1 AND a.status = 'active'
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def update_price_alert(ad_id: int, active: bool = None, triggered_at: str = None):
    """Update price alert status"""
    with get_connection() as conn:
        cursor = conn.cursor()
        updates = []
        params = []

        if active is not None:
            updates.append("active = ?")
            params.append(active)

        if triggered_at is not None:
            updates.append("triggered_at = ?")
            params.append(triggered_at)

        if not updates:
            return

        params.append(ad_id)
        cursor.execute(f"""
            UPDATE price_alerts SET {', '.join(updates)} WHERE ad_id = ?
        """, params)
        conn.commit()


def delete_price_alert(ad_id: int):
    """Delete price alert for an ad"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM price_alerts WHERE ad_id = ?", (ad_id,))
        conn.commit()


def mark_alert_triggered(ad_id: int):
    """Mark alert as triggered (won't fire again until reset)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE price_alerts
            SET triggered_at = CURRENT_TIMESTAMP
            WHERE ad_id = ?
        """, (ad_id,))
        conn.commit()


# ==================== PUSH SUBSCRIPTIONS ====================

def save_push_subscription(endpoint: str, p256dh: str, auth: str):
    """Save or update a push subscription"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO push_subscriptions (endpoint, p256dh, auth)
            VALUES (?, ?, ?)
            ON CONFLICT(endpoint) DO UPDATE SET
                p256dh = excluded.p256dh,
                auth = excluded.auth
        """, (endpoint, p256dh, auth))
        conn.commit()


def get_all_push_subscriptions():
    """Get all push subscriptions for sending notifications"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT endpoint, p256dh, auth FROM push_subscriptions")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def delete_push_subscription(endpoint: str):
    """Delete a push subscription (e.g., when it's invalid)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM push_subscriptions WHERE endpoint = ?", (endpoint,))
        conn.commit()
