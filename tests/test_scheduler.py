"""
Tests for scheduler - job execution and task management
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime


class TestSchedulerLogs:
    """Tests for scheduler logging functionality"""

    def test_add_log_stores_message_with_timestamp(self):
        """Should add log entry with timestamp and level"""
        from services.scheduler import add_log, get_logs, clear_logs

        clear_logs()
        add_log("Test message", "info")

        logs = get_logs()
        assert len(logs) == 1
        assert logs[0]['message'] == "Test message"
        assert logs[0]['level'] == "info"
        assert 'timestamp' in logs[0]

    def test_logs_are_limited_to_max_size(self):
        """Should keep only last MAX_LOGS entries"""
        from services.scheduler import add_log, get_logs, clear_logs, MAX_LOGS

        clear_logs()

        # Add more than MAX_LOGS
        for i in range(MAX_LOGS + 10):
            add_log(f"Message {i}", "info")

        logs = get_logs()
        assert len(logs) == MAX_LOGS

    def test_clear_logs_removes_all_entries(self):
        """Should remove all log entries"""
        from services.scheduler import add_log, get_logs, clear_logs

        add_log("Test", "info")
        clear_logs()

        assert get_logs() == []


class TestSchedulerTaskStatus:
    """Tests for task running status tracking"""

    def test_get_task_status_returns_running_state(self):
        """Should return current running state and result"""
        from services.scheduler import get_task_status, running_tasks, task_results

        # Reset state
        running_tasks['search'] = False
        task_results['search'] = {'success': True, 'total_new': 5}

        status = get_task_status('search')

        assert status['running'] is False
        assert status['result']['success'] is True
        assert status['result']['total_new'] == 5

    def test_get_task_status_unknown_task(self):
        """Should return False for unknown task"""
        from services.scheduler import get_task_status

        status = get_task_status('nonexistent')

        assert status['running'] is False
        assert status['result'] is None


class TestRunTaskNow:
    """Tests for manual task execution"""

    @patch('services.scheduler.threading.Thread')
    def test_run_search_now_starts_thread(self, mock_thread):
        """Should start search job in separate thread"""
        from services.scheduler import run_search_now, running_tasks

        running_tasks['search'] = False
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        result = run_search_now()

        assert result is True
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()

    def test_run_search_now_returns_false_if_already_running(self):
        """Should return False if search is already running"""
        from services.scheduler import run_search_now, running_tasks

        running_tasks['search'] = True

        result = run_search_now()

        assert result is False
        running_tasks['search'] = False  # Reset

    @patch('services.scheduler.threading.Thread')
    def test_run_price_check_now_starts_thread(self, mock_thread):
        """Should start price check job in separate thread"""
        from services.scheduler import run_price_check_now, running_tasks

        running_tasks['price_check'] = False
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        result = run_price_check_now()

        assert result is True
        mock_thread.assert_called_once()

    @patch('services.scheduler.threading.Thread')
    def test_run_status_check_now_starts_thread(self, mock_thread):
        """Should start status check job in separate thread"""
        from services.scheduler import run_status_check_now, running_tasks

        running_tasks['status_check'] = False
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        result = run_status_check_now()

        assert result is True
        mock_thread.assert_called_once()


class TestSchedulerStatus:
    """Tests for scheduler status reporting"""

    @patch('services.scheduler.scheduler')
    def test_get_scheduler_status_when_running(self, mock_scheduler):
        """Should return running status and job list"""
        from services.scheduler import get_scheduler_status

        mock_job = MagicMock()
        mock_job.id = 'search_new_ads'
        mock_job.name = 'Buscar novos anúncios'
        mock_job.next_run_time = datetime(2025, 1, 31, 12, 0, 0)

        mock_scheduler.running = True
        mock_scheduler.get_jobs.return_value = [mock_job]

        status = get_scheduler_status()

        assert status['running'] is True
        assert len(status['jobs']) == 1
        assert status['jobs'][0]['id'] == 'search_new_ads'

    @patch('services.scheduler.scheduler')
    def test_get_scheduler_status_when_stopped(self, mock_scheduler):
        """Should return empty jobs when scheduler is stopped"""
        from services.scheduler import get_scheduler_status

        mock_scheduler.running = False

        status = get_scheduler_status()

        assert status['running'] is False
        assert status['jobs'] == []


class TestJobSearchNewAdsAsync:
    """Tests for async search job"""

    @pytest.mark.asyncio
    @patch('services.scheduler.get_active_searches')
    @patch('services.scheduler.scraper')
    @patch('services.scheduler.create_ad')
    @patch('services.scheduler.get_existing_urls')
    async def test_job_finds_and_saves_new_ads(
        self, mock_existing, mock_create, mock_scraper, mock_searches
    ):
        """Should find new ads and save them to database"""
        from services.scheduler import job_search_new_ads_async, running_tasks, task_results, clear_logs

        clear_logs()
        running_tasks['search'] = False

        # Mock search config
        mock_searches.return_value = [{
            'id': 1,
            'name': 'Test Search',
            'base_url': 'https://olx.com.br/games',
            'queries': '["nintendo"]',
            'categories': '[]',
            'exclude_keywords': '[]',
            'active': True
        }]

        # Mock scraper
        mock_scraper.build_search_url.return_value = 'https://olx.com.br/games?q=nintendo'
        mock_scraper.get_ad_urls_async = AsyncMock(return_value=[
            'https://olx.com.br/ad-1',
            'https://olx.com.br/ad-2'
        ])

        mock_ad = MagicMock()
        mock_ad.url = 'https://olx.com.br/ad-1'
        mock_ad.title = 'Nintendo Switch'
        mock_ad.price = '1500,00'
        mock_ad.description = 'Test'
        mock_ad.state = 'SP'
        mock_ad.municipality = 'São Paulo'
        mock_ad.neighbourhood = 'Centro'
        mock_ad.zipcode = '01310100'
        mock_ad.seller = 'Seller'
        mock_ad.condition = 'Usado'
        mock_ad.published_at = '2025-01-01'
        mock_ad.main_category = 'Games'
        mock_ad.sub_category = 'Consoles'
        mock_ad.hobbie_type = ''
        mock_ad.images = []
        mock_ad.olx_pay = False
        mock_ad.olx_delivery = False

        mock_scraper.get_ad_info_async = AsyncMock(return_value=mock_ad)
        mock_scraper.close = AsyncMock()

        # No existing URLs
        mock_existing.return_value = set()

        await job_search_new_ads_async()

        # Should have called create_ad for new ads
        assert mock_create.called
        assert task_results['search']['success'] is True


class TestJobCheckPricesAsync:
    """Tests for async price check job"""

    @pytest.mark.asyncio
    @patch('services.scheduler.get_watching_ads')
    @patch('services.scheduler.scraper')
    @patch('services.scheduler.get_last_price_check')
    @patch('services.scheduler.add_price_history')
    @patch('services.scheduler.update_ad_price')
    @patch('services.scheduler.notify_price_drop')
    async def test_job_detects_price_changes(
        self, mock_notify, mock_update, mock_history, mock_last, mock_scraper, mock_watching
    ):
        """Should detect and record price changes"""
        from services.scheduler import job_check_prices_async, running_tasks, task_results, clear_logs

        clear_logs()
        running_tasks['price_check'] = False

        # Mock watching ad
        mock_watching.return_value = [{
            'id': 1,
            'url': 'https://olx.com.br/ad-1',
            'title': 'Nintendo Switch',
            'price': '1500,00',
            'images': '[]'
        }]

        # Mock scraper returning new price
        mock_scraper.get_current_price_async = AsyncMock(return_value='1200,00')
        mock_scraper.close = AsyncMock()

        # Last price was different
        mock_last.return_value = {'price': '1500,00'}

        await job_check_prices_async()

        # Should have updated price
        mock_update.assert_called_once_with(1, '1200,00')
        mock_history.assert_called()
        assert task_results['price_check']['success'] is True


class TestJobCheckAdStatusAsync:
    """Tests for async ad status check job"""

    @pytest.mark.asyncio
    @patch('services.scheduler.get_ads_to_check')
    @patch('services.scheduler.scraper')
    @patch('services.scheduler.update_ad_status')
    async def test_job_marks_inactive_ads(
        self, mock_update, mock_scraper, mock_ads
    ):
        """Should mark ads as inactive when they're removed from OLX"""
        from services.scheduler import job_check_ad_status_async, running_tasks, task_results, clear_logs

        clear_logs()
        running_tasks['status_check'] = False

        # Mock ads to check
        mock_ads.return_value = [
            {'id': 1, 'url': 'https://olx.com.br/ad-1'},
            {'id': 2, 'url': 'https://olx.com.br/ad-2'},
        ]

        # First ad is active, second is inactive
        mock_scraper.check_ad_status_async = AsyncMock(side_effect=['active', 'inactive'])
        mock_scraper.close = AsyncMock()

        await job_check_ad_status_async()

        # Should have marked ad 2 as inactive
        mock_update.assert_called_once_with(2, 'inactive')
        assert task_results['status_check']['success'] is True
        assert task_results['status_check']['deactivated'] == 1
