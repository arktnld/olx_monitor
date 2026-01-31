"""
Tests for database operations
"""

import pytest
import json
import sqlite3
from contextlib import contextmanager
from unittest.mock import patch


class TestDatabaseOperations:
    """Tests for database CRUD operations using in-memory DB"""

    @contextmanager
    def _patch_db(self, in_memory_db):
        """Helper to patch database connection"""
        @contextmanager
        def mock_connection():
            yield in_memory_db

        with patch('services.database.get_connection', mock_connection):
            yield

    def test_create_and_get_search(self, in_memory_db, sample_search_data):
        """Should create and retrieve a search"""
        with self._patch_db(in_memory_db):
            from services.database import create_search, get_search_by_id

            search_id = create_search(
                name=sample_search_data['name'],
                base_url=sample_search_data['base_url'],
                queries=json.loads(sample_search_data['queries']),
                categories=json.loads(sample_search_data['categories']),
                exclude_keywords=json.loads(sample_search_data['exclude_keywords']),
                state=sample_search_data['state'],
                region=sample_search_data['region'],
                category=sample_search_data['category'],
                subcategory=sample_search_data['subcategory']
            )

            assert search_id == 1

            search = get_search_by_id(search_id)
            assert search is not None
            assert search['name'] == 'Nintendo Switch'

    def test_get_all_searches(self, in_memory_db):
        """Should return all searches"""
        with self._patch_db(in_memory_db):
            from services.database import create_search, get_all_searches

            create_search('Search 1', 'https://olx.com.br/1', [], [], [])
            create_search('Search 2', 'https://olx.com.br/2', [], [], [])

            searches = get_all_searches()
            assert len(searches) == 2

    def test_get_active_searches(self, in_memory_db):
        """Should return only active searches"""
        with self._patch_db(in_memory_db):
            from services.database import create_search, get_active_searches, toggle_search_active

            id1 = create_search('Active', 'https://olx.com.br/1', [], [], [])
            id2 = create_search('Inactive', 'https://olx.com.br/2', [], [], [])

            # Deactivate second search
            toggle_search_active(id2)

            searches = get_active_searches()
            assert len(searches) == 1
            assert searches[0]['name'] == 'Active'

    def test_delete_search(self, in_memory_db):
        """Should delete a search"""
        with self._patch_db(in_memory_db):
            from services.database import create_search, delete_search, get_search_by_id

            search_id = create_search('To Delete', 'https://olx.com.br/1', [], [], [])
            delete_search(search_id)

            search = get_search_by_id(search_id)
            assert search is None

    def test_create_and_get_ad(self, in_memory_db):
        """Should create and retrieve an ad"""
        with self._patch_db(in_memory_db):
            from services.database import create_ad, get_ad_by_id

            ad_id = create_ad(
                url='https://sp.olx.com.br/item-123',
                title='Test Item',
                price='100,00',
                description='Test description',
                state='#SP',
                municipality='São Paulo',
                neighbourhood='Centro',
                zipcode='01310100',
                seller='Seller Name',
                condition='Usado',
                published_at='2025-01-15',
                main_category='Games',
                sub_category='Consoles',
                hobbie_type='',
                images=['img1.jpg', 'img2.jpg'],
                olx_pay=True,
                olx_delivery=False,
                search_id=1
            )

            assert ad_id == 1

            ad = get_ad_by_id(ad_id)
            assert ad is not None
            assert ad['title'] == 'Test Item'
            assert ad['price'] == '100,00'

    def test_ad_exists(self, in_memory_db):
        """Should check if ad exists by URL"""
        with self._patch_db(in_memory_db):
            from services.database import create_ad, ad_exists

            url = 'https://sp.olx.com.br/item-123'
            assert ad_exists(url) is False

            create_ad(
                url=url,
                title='Test',
                price='100',
                description='',
                state='',
                municipality='',
                neighbourhood='',
                zipcode='',
                seller='',
                condition='',
                published_at='',
                main_category='',
                sub_category='',
                hobbie_type='',
                images=[],
                olx_pay=False,
                olx_delivery=False,
                search_id=1
            )

            assert ad_exists(url) is True

    def test_get_existing_urls(self, in_memory_db):
        """Should batch check existing URLs"""
        with self._patch_db(in_memory_db):
            from services.database import create_ad, get_existing_urls

            create_ad(
                url='https://olx.com.br/item-1',
                title='Item 1', price='100', description='', state='',
                municipality='', neighbourhood='', zipcode='', seller='',
                condition='', published_at='', main_category='', sub_category='',
                hobbie_type='', images=[], olx_pay=False, olx_delivery=False, search_id=1
            )
            create_ad(
                url='https://olx.com.br/item-2',
                title='Item 2', price='200', description='', state='',
                municipality='', neighbourhood='', zipcode='', seller='',
                condition='', published_at='', main_category='', sub_category='',
                hobbie_type='', images=[], olx_pay=False, olx_delivery=False, search_id=1
            )

            urls_to_check = [
                'https://olx.com.br/item-1',
                'https://olx.com.br/item-2',
                'https://olx.com.br/item-3',
            ]

            existing = get_existing_urls(urls_to_check)

            assert len(existing) == 2
            assert 'https://olx.com.br/item-1' in existing
            assert 'https://olx.com.br/item-2' in existing
            assert 'https://olx.com.br/item-3' not in existing

    def test_mark_ad_seen(self, in_memory_db):
        """Should mark ad as seen"""
        with self._patch_db(in_memory_db):
            from services.database import create_ad, mark_ad_seen, get_ad_by_id

            ad_id = create_ad(
                url='https://olx.com.br/item-1',
                title='Test', price='100', description='', state='',
                municipality='', neighbourhood='', zipcode='', seller='',
                condition='', published_at='', main_category='', sub_category='',
                hobbie_type='', images=[], olx_pay=False, olx_delivery=False, search_id=1
            )

            ad = get_ad_by_id(ad_id)
            assert ad['seen'] == 0

            mark_ad_seen(ad_id)

            ad = get_ad_by_id(ad_id)
            assert ad['seen'] == 1

    def test_update_ad_status(self, in_memory_db):
        """Should update ad status"""
        with self._patch_db(in_memory_db):
            from services.database import create_ad, update_ad_status, get_ad_by_id

            ad_id = create_ad(
                url='https://olx.com.br/item-1',
                title='Test', price='100', description='', state='',
                municipality='', neighbourhood='', zipcode='', seller='',
                condition='', published_at='', main_category='', sub_category='',
                hobbie_type='', images=[], olx_pay=False, olx_delivery=False, search_id=1
            )

            update_ad_status(ad_id, 'inactive')

            ad = get_ad_by_id(ad_id)
            assert ad['status'] == 'inactive'
            assert ad['deactivated_at'] is not None


class TestPriceHistory:
    """Tests for price history operations"""

    @contextmanager
    def _patch_db(self, in_memory_db):
        @contextmanager
        def mock_connection():
            yield in_memory_db

        with patch('services.database.get_connection', mock_connection):
            yield

    def test_add_and_get_price_history(self, in_memory_db):
        """Should add and retrieve price history"""
        with self._patch_db(in_memory_db):
            from services.database import create_ad, add_price_history, get_price_history

            ad_id = create_ad(
                url='https://olx.com.br/item-1',
                title='Test', price='100', description='', state='',
                municipality='', neighbourhood='', zipcode='', seller='',
                condition='', published_at='', main_category='', sub_category='',
                hobbie_type='', images=[], olx_pay=False, olx_delivery=False, search_id=1
            )

            add_price_history(ad_id, '100,00')
            add_price_history(ad_id, '90,00')
            add_price_history(ad_id, '80,00')

            history = get_price_history(ad_id)
            assert len(history) == 3
            assert history[0]['price'] == '100,00'
            assert history[-1]['price'] == '80,00'


class TestPriceAlerts:
    """Tests for price alerts operations"""

    @contextmanager
    def _patch_db(self, in_memory_db):
        @contextmanager
        def mock_connection():
            yield in_memory_db

        with patch('services.database.get_connection', mock_connection):
            yield

    def test_create_and_get_price_alert(self, in_memory_db):
        """Should create and retrieve price alert"""
        with self._patch_db(in_memory_db):
            from services.database import create_ad, create_price_alert, get_price_alert

            ad_id = create_ad(
                url='https://olx.com.br/item-1',
                title='Test', price='100', description='', state='',
                municipality='', neighbourhood='', zipcode='', seller='',
                condition='', published_at='', main_category='', sub_category='',
                hobbie_type='', images=[], olx_pay=False, olx_delivery=False, search_id=1
            )

            create_price_alert(ad_id, target_price=80.0, notify_below=True)

            alert = get_price_alert(ad_id)
            assert alert is not None
            assert alert['target_price'] == 80.0
            assert alert['notify_below'] == 1

    def test_delete_price_alert(self, in_memory_db):
        """Should delete price alert"""
        with self._patch_db(in_memory_db):
            from services.database import create_ad, create_price_alert, delete_price_alert, get_price_alert

            ad_id = create_ad(
                url='https://olx.com.br/item-1',
                title='Test', price='100', description='', state='',
                municipality='', neighbourhood='', zipcode='', seller='',
                condition='', published_at='', main_category='', sub_category='',
                hobbie_type='', images=[], olx_pay=False, olx_delivery=False, search_id=1
            )

            create_price_alert(ad_id, target_price=80.0)
            delete_price_alert(ad_id)

            alert = get_price_alert(ad_id)
            assert alert is None


class TestSettings:
    """Tests for settings operations"""

    @contextmanager
    def _patch_db(self, in_memory_db):
        @contextmanager
        def mock_connection():
            yield in_memory_db

        with patch('services.database.get_connection', mock_connection):
            yield

    def test_get_and_set_setting(self, in_memory_db):
        """Should get and set settings"""
        with self._patch_db(in_memory_db):
            from services.database import get_setting, set_setting

            # Default value
            assert get_setting('nonexistent', 'default') == 'default'

            # Set and get
            set_setting('test_key', 'test_value')
            assert get_setting('test_key') == 'test_value'

            # Update existing
            set_setting('test_key', 'new_value')
            assert get_setting('test_key') == 'new_value'


class TestGetAdsWithFilters:
    """Tests for get_ads with various filters"""

    @contextmanager
    def _patch_db(self, in_memory_db):
        @contextmanager
        def mock_connection():
            yield in_memory_db

        with patch('services.database.get_connection', mock_connection):
            yield

    def _create_test_ads(self):
        """Helper to create test ads"""
        from services.database import create_ad, mark_ad_seen

        # Ad 1: cheap, SP, not seen
        ad1 = create_ad(
            url='https://olx.com.br/item-1',
            title='Nintendo Switch Lite',
            price='800,00',
            description='Console portátil',
            state='#SP',
            municipality='São Paulo',
            neighbourhood='Centro',
            zipcode='01310100',
            seller='Seller 1',
            condition='Usado',
            published_at='2025-01-01',
            main_category='Games',
            sub_category='Consoles',
            hobbie_type='',
            images=[],
            olx_pay=False,
            olx_delivery=False,
            search_id=1
        )

        # Ad 2: expensive, RJ, seen
        ad2 = create_ad(
            url='https://olx.com.br/item-2',
            title='PlayStation 5',
            price='4.500,00',
            description='Console novo',
            state='#RJ',
            municipality='Rio de Janeiro',
            neighbourhood='Copacabana',
            zipcode='22041080',
            seller='Seller 2',
            condition='Novo',
            published_at='2025-01-15',
            main_category='Games',
            sub_category='Consoles',
            hobbie_type='',
            images=[],
            olx_pay=True,
            olx_delivery=True,
            search_id=1
        )
        mark_ad_seen(ad2)

        # Ad 3: mid-price, SP, not seen
        ad3 = create_ad(
            url='https://olx.com.br/item-3',
            title='Xbox Series S',
            price='1.800,00',
            description='Console Microsoft',
            state='#SP',
            municipality='Campinas',
            neighbourhood='Centro',
            zipcode='13015100',
            seller='Seller 3',
            condition='Usado',
            published_at='2025-01-20',
            main_category='Games',
            sub_category='Consoles',
            hobbie_type='',
            images=[],
            olx_pay=False,
            olx_delivery=False,
            search_id=2
        )

        return ad1, ad2, ad3

    def test_filter_by_search_id(self, in_memory_db):
        """Should filter ads by search_id"""
        with self._patch_db(in_memory_db):
            from services.database import get_ads

            self._create_test_ads()

            ads = get_ads(search_id=1)
            assert len(ads) == 2

            ads = get_ads(search_id=2)
            assert len(ads) == 1
            assert ads[0]['title'] == 'Xbox Series S'

    def test_filter_by_status_new(self, in_memory_db):
        """Should filter only new (unseen) ads"""
        with self._patch_db(in_memory_db):
            from services.database import get_ads

            self._create_test_ads()

            ads = get_ads(status='new')
            assert len(ads) == 2
            assert all(ad['seen'] == 0 for ad in ads)

    def test_filter_by_status_seen(self, in_memory_db):
        """Should filter only seen ads"""
        with self._patch_db(in_memory_db):
            from services.database import get_ads

            self._create_test_ads()

            ads = get_ads(status='seen')
            assert len(ads) == 1
            assert ads[0]['title'] == 'PlayStation 5'

    def test_filter_by_min_price(self, in_memory_db):
        """Should filter ads by minimum price"""
        with self._patch_db(in_memory_db):
            from services.database import get_ads

            self._create_test_ads()

            ads = get_ads(min_price=1500)
            assert len(ads) == 2
            assert 'Nintendo Switch Lite' not in [ad['title'] for ad in ads]

    def test_filter_by_max_price(self, in_memory_db):
        """Should filter ads by maximum price"""
        with self._patch_db(in_memory_db):
            from services.database import get_ads

            self._create_test_ads()

            ads = get_ads(max_price=2000)
            assert len(ads) == 2
            assert 'PlayStation 5' not in [ad['title'] for ad in ads]

    def test_filter_by_state(self, in_memory_db):
        """Should filter ads by state"""
        with self._patch_db(in_memory_db):
            from services.database import get_ads

            self._create_test_ads()

            ads = get_ads(state='#SP')
            assert len(ads) == 2

            ads = get_ads(state='#RJ')
            assert len(ads) == 1
            assert ads[0]['title'] == 'PlayStation 5'

    def test_filter_by_search_text(self, in_memory_db):
        """Should filter ads by search text in title/description"""
        with self._patch_db(in_memory_db):
            from services.database import get_ads

            self._create_test_ads()

            ads = get_ads(search_text='nintendo')
            assert len(ads) == 1
            assert ads[0]['title'] == 'Nintendo Switch Lite'

            ads = get_ads(search_text='console')
            assert len(ads) == 3

    def test_sort_by_price_asc(self, in_memory_db):
        """Should sort ads by price ascending"""
        with self._patch_db(in_memory_db):
            from services.database import get_ads

            self._create_test_ads()

            ads = get_ads(sort_by='price_asc')
            assert ads[0]['title'] == 'Nintendo Switch Lite'
            assert ads[-1]['title'] == 'PlayStation 5'

    def test_sort_by_price_desc(self, in_memory_db):
        """Should sort ads by price descending"""
        with self._patch_db(in_memory_db):
            from services.database import get_ads

            self._create_test_ads()

            ads = get_ads(sort_by='price_desc')
            assert ads[0]['title'] == 'PlayStation 5'
            assert ads[-1]['title'] == 'Nintendo Switch Lite'

    def test_pagination_with_limit_offset(self, in_memory_db):
        """Should paginate results"""
        with self._patch_db(in_memory_db):
            from services.database import get_ads

            self._create_test_ads()

            ads = get_ads(limit=1, offset=0)
            assert len(ads) == 1

            ads = get_ads(limit=2, offset=1)
            assert len(ads) == 2


class TestWatchingAds:
    """Tests for watching ads functionality"""

    @contextmanager
    def _patch_db(self, in_memory_db):
        @contextmanager
        def mock_connection():
            yield in_memory_db

        with patch('services.database.get_connection', mock_connection):
            yield

    def test_get_watching_ads(self, in_memory_db):
        """Should return only watching ads"""
        with self._patch_db(in_memory_db):
            from services.database import create_ad, get_watching_ads

            # Mock download_ad_images to avoid file system operations
            with patch('services.images.download_ad_images'):
                from services.database import toggle_ad_watching

                ad1 = create_ad(
                    url='https://olx.com.br/item-1',
                    title='Item 1', price='100,00', description='', state='#SP',
                    municipality='', neighbourhood='', zipcode='', seller='',
                    condition='', published_at='', main_category='', sub_category='',
                    hobbie_type='', images=[], olx_pay=False, olx_delivery=False, search_id=1
                )
                ad2 = create_ad(
                    url='https://olx.com.br/item-2',
                    title='Item 2', price='200,00', description='', state='#RJ',
                    municipality='', neighbourhood='', zipcode='', seller='',
                    condition='', published_at='', main_category='', sub_category='',
                    hobbie_type='', images=[], olx_pay=False, olx_delivery=False, search_id=1
                )

                toggle_ad_watching(ad1)

                watching = get_watching_ads()
                assert len(watching) == 1
                assert watching[0]['title'] == 'Item 1'

    def test_get_watching_ads_with_filters(self, in_memory_db):
        """Should filter watching ads by price and state"""
        with self._patch_db(in_memory_db):
            from services.database import create_ad, get_watching_ads

            with patch('services.images.download_ad_images'):
                from services.database import toggle_ad_watching

                ad1 = create_ad(
                    url='https://olx.com.br/item-1',
                    title='Cheap SP', price='100,00', description='', state='#SP',
                    municipality='', neighbourhood='', zipcode='', seller='',
                    condition='', published_at='', main_category='', sub_category='',
                    hobbie_type='', images=[], olx_pay=False, olx_delivery=False, search_id=1
                )
                ad2 = create_ad(
                    url='https://olx.com.br/item-2',
                    title='Expensive RJ', price='500,00', description='', state='#RJ',
                    municipality='', neighbourhood='', zipcode='', seller='',
                    condition='', published_at='', main_category='', sub_category='',
                    hobbie_type='', images=[], olx_pay=False, olx_delivery=False, search_id=1
                )

                toggle_ad_watching(ad1)
                toggle_ad_watching(ad2)

                # Filter by state
                watching = get_watching_ads(state='#SP')
                assert len(watching) == 1
                assert watching[0]['title'] == 'Cheap SP'

                # Filter by price
                watching = get_watching_ads(min_price=200)
                assert len(watching) == 1
                assert watching[0]['title'] == 'Expensive RJ'


class TestInactiveAds:
    """Tests for inactive ads functionality"""

    @contextmanager
    def _patch_db(self, in_memory_db):
        @contextmanager
        def mock_connection():
            yield in_memory_db

        with patch('services.database.get_connection', mock_connection):
            yield

    def test_get_inactive_ads(self, in_memory_db):
        """Should return only inactive ads"""
        with self._patch_db(in_memory_db):
            from services.database import create_ad, update_ad_status, get_inactive_ads

            ad1 = create_ad(
                url='https://olx.com.br/item-1',
                title='Active', price='100,00', description='', state='',
                municipality='', neighbourhood='', zipcode='', seller='',
                condition='', published_at='', main_category='', sub_category='',
                hobbie_type='', images=[], olx_pay=False, olx_delivery=False, search_id=1
            )
            ad2 = create_ad(
                url='https://olx.com.br/item-2',
                title='Inactive', price='200,00', description='', state='',
                municipality='', neighbourhood='', zipcode='', seller='',
                condition='', published_at='', main_category='', sub_category='',
                hobbie_type='', images=[], olx_pay=False, olx_delivery=False, search_id=1
            )

            update_ad_status(ad2, 'inactive')

            inactive = get_inactive_ads()
            assert len(inactive) == 1
            assert inactive[0]['title'] == 'Inactive'


class TestPushSubscriptions:
    """Tests for push subscriptions CRUD"""

    @contextmanager
    def _patch_db(self, in_memory_db):
        @contextmanager
        def mock_connection():
            yield in_memory_db

        with patch('services.database.get_connection', mock_connection):
            yield

    def test_save_and_get_subscription(self, in_memory_db):
        """Should save and retrieve push subscription"""
        with self._patch_db(in_memory_db):
            from services.database import save_push_subscription, get_all_push_subscriptions

            save_push_subscription(
                endpoint='https://push.example.com/send/abc123',
                p256dh='BNcRd...',
                auth='tBHI...'
            )

            subs = get_all_push_subscriptions()
            assert len(subs) == 1
            assert subs[0]['endpoint'] == 'https://push.example.com/send/abc123'

    def test_update_existing_subscription(self, in_memory_db):
        """Should update subscription on conflict"""
        with self._patch_db(in_memory_db):
            from services.database import save_push_subscription, get_all_push_subscriptions

            endpoint = 'https://push.example.com/send/abc123'

            save_push_subscription(endpoint, 'old_p256dh', 'old_auth')
            save_push_subscription(endpoint, 'new_p256dh', 'new_auth')

            subs = get_all_push_subscriptions()
            assert len(subs) == 1
            assert subs[0]['p256dh'] == 'new_p256dh'

    def test_delete_subscription(self, in_memory_db):
        """Should delete push subscription"""
        with self._patch_db(in_memory_db):
            from services.database import save_push_subscription, delete_push_subscription, get_all_push_subscriptions

            endpoint = 'https://push.example.com/send/abc123'
            save_push_subscription(endpoint, 'p256dh', 'auth')
            delete_push_subscription(endpoint)

            subs = get_all_push_subscriptions()
            assert len(subs) == 0


class TestAdditionalOperations:
    """Tests for additional database operations"""

    @contextmanager
    def _patch_db(self, in_memory_db):
        @contextmanager
        def mock_connection():
            yield in_memory_db

        with patch('services.database.get_connection', mock_connection):
            yield

    def test_update_ad_price(self, in_memory_db):
        """Should update ad price"""
        with self._patch_db(in_memory_db):
            from services.database import create_ad, update_ad_price, get_ad_by_id

            ad_id = create_ad(
                url='https://olx.com.br/item-1',
                title='Test', price='100,00', description='', state='',
                municipality='', neighbourhood='', zipcode='', seller='',
                condition='', published_at='', main_category='', sub_category='',
                hobbie_type='', images=[], olx_pay=False, olx_delivery=False, search_id=1
            )

            update_ad_price(ad_id, '80,00')

            ad = get_ad_by_id(ad_id)
            assert ad['price'] == '80,00'

    def test_get_last_price_check(self, in_memory_db):
        """Should return most recent price check (by ID since timestamps can be identical)"""
        with self._patch_db(in_memory_db):
            from services.database import create_ad, add_price_history, get_last_price_check, get_price_history

            ad_id = create_ad(
                url='https://olx.com.br/item-1',
                title='Test', price='100', description='', state='',
                municipality='', neighbourhood='', zipcode='', seller='',
                condition='', published_at='', main_category='', sub_category='',
                hobbie_type='', images=[], olx_pay=False, olx_delivery=False, search_id=1
            )

            add_price_history(ad_id, '100,00')

            last = get_last_price_check(ad_id)
            assert last is not None
            assert last['price'] == '100,00'

            # Add another and verify it returns the newest
            add_price_history(ad_id, '80,00')

            # Get all history to see which was added last
            history = get_price_history(ad_id)
            assert len(history) == 2

            last = get_last_price_check(ad_id)
            assert last is not None

    def test_get_ads_to_check(self, in_memory_db):
        """Should return active ads for status checking"""
        with self._patch_db(in_memory_db):
            from services.database import create_ad, update_ad_status, get_ads_to_check

            ad1 = create_ad(
                url='https://olx.com.br/item-1',
                title='Active', price='100', description='', state='',
                municipality='', neighbourhood='', zipcode='', seller='',
                condition='', published_at='', main_category='', sub_category='',
                hobbie_type='', images=[], olx_pay=False, olx_delivery=False, search_id=1
            )
            ad2 = create_ad(
                url='https://olx.com.br/item-2',
                title='Inactive', price='200', description='', state='',
                municipality='', neighbourhood='', zipcode='', seller='',
                condition='', published_at='', main_category='', sub_category='',
                hobbie_type='', images=[], olx_pay=False, olx_delivery=False, search_id=1
            )

            update_ad_status(ad2, 'inactive')

            ads = get_ads_to_check()
            assert len(ads) == 1
            assert ads[0]['url'] == 'https://olx.com.br/item-1'

    def test_get_ads_count(self, in_memory_db):
        """Should count ads with filters"""
        with self._patch_db(in_memory_db):
            from services.database import create_ad, get_ads_count

            for i in range(5):
                create_ad(
                    url=f'https://olx.com.br/item-{i}',
                    title=f'Item {i}', price='100', description='', state='#SP',
                    municipality='', neighbourhood='', zipcode='', seller='',
                    condition='', published_at='', main_category='', sub_category='',
                    hobbie_type='', images=[], olx_pay=False, olx_delivery=False, search_id=1
                )

            count = get_ads_count()
            assert count == 5

            count = get_ads_count(state='#SP')
            assert count == 5

            count = get_ads_count(state='#RJ')
            assert count == 0

    def test_get_distinct_states(self, in_memory_db):
        """Should return unique states"""
        with self._patch_db(in_memory_db):
            from services.database import create_ad, get_distinct_states

            create_ad(
                url='https://olx.com.br/item-1',
                title='Item 1', price='100', description='', state='#SP',
                municipality='', neighbourhood='', zipcode='', seller='',
                condition='', published_at='', main_category='', sub_category='',
                hobbie_type='', images=[], olx_pay=False, olx_delivery=False, search_id=1
            )
            create_ad(
                url='https://olx.com.br/item-2',
                title='Item 2', price='100', description='', state='#RJ',
                municipality='', neighbourhood='', zipcode='', seller='',
                condition='', published_at='', main_category='', sub_category='',
                hobbie_type='', images=[], olx_pay=False, olx_delivery=False, search_id=1
            )
            create_ad(
                url='https://olx.com.br/item-3',
                title='Item 3', price='100', description='', state='#SP',
                municipality='', neighbourhood='', zipcode='', seller='',
                condition='', published_at='', main_category='', sub_category='',
                hobbie_type='', images=[], olx_pay=False, olx_delivery=False, search_id=1
            )

            states = get_distinct_states()
            assert len(states) == 2
            assert '#SP' in states
            assert '#RJ' in states

    def test_update_search(self, in_memory_db):
        """Should update search configuration"""
        with self._patch_db(in_memory_db):
            from services.database import create_search, update_search, get_search_by_id

            search_id = create_search(
                name='Original',
                base_url='https://olx.com.br/original',
                queries=['query1'],
                categories=[],
                exclude_keywords=[]
            )

            update_search(
                search_id=search_id,
                name='Updated',
                base_url='https://olx.com.br/updated',
                queries=['query2'],
                categories=['cat1'],
                exclude_keywords=['exclude1'],
                active=True
            )

            search = get_search_by_id(search_id)
            assert search['name'] == 'Updated'
            assert search['base_url'] == 'https://olx.com.br/updated'

    def test_mark_alert_triggered(self, in_memory_db):
        """Should mark price alert as triggered"""
        with self._patch_db(in_memory_db):
            from services.database import create_ad, create_price_alert, mark_alert_triggered, get_price_alert

            ad_id = create_ad(
                url='https://olx.com.br/item-1',
                title='Test', price='100', description='', state='',
                municipality='', neighbourhood='', zipcode='', seller='',
                condition='', published_at='', main_category='', sub_category='',
                hobbie_type='', images=[], olx_pay=False, olx_delivery=False, search_id=1
            )

            create_price_alert(ad_id, target_price=80.0)
            mark_alert_triggered(ad_id)

            alert = get_price_alert(ad_id)
            assert alert['triggered_at'] is not None
