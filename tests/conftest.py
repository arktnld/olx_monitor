"""
Shared fixtures for OLX Monitor tests
"""

import pytest
import sqlite3
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def sample_ad_data():
    """Sample ad data for testing"""
    return {
        'id': 1,
        'url': 'https://sp.olx.com.br/sao-paulo/games/nintendo-switch-123456789',
        'title': 'Nintendo Switch Completo',
        'price': '1.500,00',
        'description': 'Nintendo Switch em ótimo estado, com todos os acessórios.',
        'state': '#SP',
        'municipality': 'São Paulo',
        'neighbourhood': 'Centro',
        'zipcode': '01310100',
        'seller': 'João Silva',
        'condition': 'Usado',
        'published_at': '2025-01-15',
        'main_category': 'Games',
        'sub_category': 'Consoles',
        'hobbie_type': '',
        'images': '["https://img.olx.com.br/image1.jpg", "https://img.olx.com.br/image2.jpg"]',
        'olx_pay': True,
        'olx_delivery': False,
        'search_id': 1,
        'found_at': '2025-01-20 10:00:00',
        'seen': False,
        'watching': False,
        'status': 'active',
        'deactivated_at': None
    }


@pytest.fixture
def sample_search_data():
    """Sample search data for testing"""
    return {
        'id': 1,
        'name': 'Nintendo Switch',
        'base_url': 'https://sp.olx.com.br/sao-paulo/games',
        'queries': '["nintendo switch", "switch oled"]',
        'categories': '["games"]',
        'exclude_keywords': '["lite", "broken"]',
        'active': True,
        'state': 'SP',
        'region': 'sao-paulo',
        'category': 'games',
        'subcategory': 'consoles',
        'cheap_threshold': 150.0
    }


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for testing"""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Create tables
    cursor.execute("""
        CREATE TABLE searches (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE,
            base_url TEXT,
            queries TEXT,
            categories TEXT,
            exclude_keywords TEXT,
            active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            state TEXT DEFAULT '',
            region TEXT DEFAULT '',
            category TEXT DEFAULT 'games',
            subcategory TEXT DEFAULT '',
            cheap_threshold REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE ads (
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
            cheap_threshold REAL,
            FOREIGN KEY (search_id) REFERENCES searches(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE price_history (
            id INTEGER PRIMARY KEY,
            ad_id INTEGER,
            price TEXT,
            checked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ad_id) REFERENCES ads(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE price_alerts (
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
        CREATE TABLE push_subscriptions (
            id INTEGER PRIMARY KEY,
            endpoint TEXT UNIQUE,
            p256dh TEXT,
            auth TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE notification_history (
            id INTEGER PRIMARY KEY,
            type TEXT NOT NULL,
            ad_id INTEGER,
            title TEXT,
            price TEXT,
            old_price TEXT,
            target_price REAL,
            url TEXT,
            image TEXT,
            search_name TEXT,
            sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            success INTEGER DEFAULT 1,
            read_at DATETIME,
            FOREIGN KEY (ad_id) REFERENCES ads(id)
        )
    """)

    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def mock_db_connection(in_memory_db):
    """Mock the database connection to use in-memory DB"""
    with patch('services.database.get_connection') as mock:
        mock.return_value.__enter__ = MagicMock(return_value=in_memory_db)
        mock.return_value.__exit__ = MagicMock(return_value=False)
        yield in_memory_db


@pytest.fixture
def sample_olx_search_html():
    """Sample OLX search results page HTML"""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>OLX - Resultados</title></head>
    <body>
        <div class="results">
            <a href="https://sp.olx.com.br/sao-paulo/games/nintendo-switch-123456789">Ad 1</a>
            <a href="https://sp.olx.com.br/sao-paulo/games/ps5-987654321">Ad 2</a>
            <a href="https://sp.olx.com.br/sao-paulo/games/xbox-series-x-456789123">Ad 3</a>
            <a href="https://www.google.com/other-link">Not OLX</a>
            <a href="/relative/link">Relative</a>
        </div>
    </body>
    </html>
    """.encode('utf-8')


@pytest.fixture
def sample_olx_ad_html():
    """Sample OLX ad page HTML with data layer"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Nintendo Switch - OLX</title>
        <script type="application/ld+json">
        {
            "description": "Nintendo Switch em ótimo estado",
            "image": [
                {"contentUrl": "https://img.olx.com.br/image1.jpg"},
                {"contentUrl": "https://img.olx.com.br/image2.jpg"}
            ]
        }
        </script>
        <script>
        window.dataLayer = [{
            "page": {
                "detail": {
                    "price": "1.500,00",
                    "zipcode": "01310100",
                    "olxPay": {"enabled": true},
                    "olxDelivery": {"enabled": false}
                },
                "adDetail": {
                    "subject": "Nintendo Switch Completo",
                    "state": "SP",
                    "municipality": "São Paulo",
                    "neighbourhood": "Centro",
                    "sellerName": "João Silva",
                    "hobbies_condition": "Usado",
                    "adDate": "2025-01-15",
                    "mainCategory": "Games",
                    "subCategory": "Consoles",
                    "hobbies_collections_type": ""
                }
            }
        }];
        </script>
    </head>
    <body>
        <h1>Nintendo Switch Completo</h1>
        <p>R$ 1.500,00</p>
    </body>
    </html>
    """.encode('utf-8')


@pytest.fixture
def sample_olx_inactive_html():
    """Sample OLX page for inactive/removed ad"""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Página não encontrada - OLX</title></head>
    <body>
        <h1>Página não foi encontrada</h1>
        <p>O anúncio que você procura não existe mais.</p>
    </body>
    </html>
    """.encode('utf-8')
