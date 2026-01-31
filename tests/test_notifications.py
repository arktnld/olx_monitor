"""
Tests for notification service - price parsing and push notifications
"""

import pytest
from unittest.mock import patch, MagicMock

from services.notifications import (
    parse_price,
    is_price_drop,
    is_cheap_ad,
    check_price_alert_trigger,
)


class TestParsePrice:
    """Tests for Brazilian price format parsing"""

    @pytest.mark.parametrize("price_str,expected", [
        ('100', 100.0),
        ('50', 50.0),
        ('100,50', 100.50),
        ('99,99', 99.99),
        ('1.500,00', 1500.00),
        ('10.000', 10000.0),
        ('1.234.567,89', 1234567.89),
    ])
    def test_parses_brazilian_price_formats(self, price_str, expected):
        """Should correctly parse prices with comma decimals and dot thousands"""
        assert parse_price(price_str) == expected


class TestIsPriceDrop:
    """Tests for price drop detection logic"""

    @pytest.mark.parametrize("old_price,new_price,expected", [
        ('200,00', '150,00', True),       # price dropped
        ('1.500,00', '1.200,00', True),   # price dropped with thousands
        ('100,00', '150,00', False),      # price increased
        ('100,00', '100,00', False),      # price unchanged
        ('invalid', '100,00', False),     # invalid old price
        ('100,00', 'invalid', False),     # invalid new price
    ])
    def test_detects_price_changes_correctly(self, old_price, new_price, expected):
        """Should detect when price dropped vs increased vs unchanged"""
        assert is_price_drop(old_price, new_price) is expected


class TestIsCheapAd:
    """Tests for cheap ad threshold detection"""

    @pytest.mark.parametrize("price,threshold,expected", [
        ('100,00', 150.0, True),    # below default threshold
        ('150,00', 150.0, True),    # exactly at threshold
        ('151,00', 150.0, False),   # above threshold
        ('500,00', 150.0, False),   # well above threshold
        ('200,00', 250.0, True),    # custom threshold - below
        ('300,00', 250.0, False),   # custom threshold - above
        ('invalid', 150.0, False),  # invalid price
    ])
    def test_detects_cheap_ads_based_on_threshold(self, price, threshold, expected):
        """Should correctly identify ads at or below price threshold"""
        assert is_cheap_ad(price, threshold=threshold) is expected


class TestCheckPriceAlertTrigger:
    """Tests for price alert trigger conditions"""

    @pytest.mark.parametrize("current_price,target,notify_below,expected", [
        # notify_below=True: trigger when price <= target
        ('80,00', 100.0, True, True),     # below target
        ('100,00', 100.0, True, True),    # exactly at target
        ('150,00', 100.0, True, False),   # above target

        # notify_below=False: trigger when price >= target
        ('150,00', 100.0, False, True),   # above target
        ('100,00', 100.0, False, True),   # exactly at target
        ('80,00', 100.0, False, False),   # below target

        # Invalid prices should never trigger
        ('invalid', 100.0, True, False),
    ])
    def test_triggers_alert_based_on_conditions(self, current_price, target, notify_below, expected):
        """Should trigger alert when price meets target condition"""
        assert check_price_alert_trigger(current_price, target, notify_below) is expected


class TestSendPushNotification:
    """Tests for push notification delivery"""

    @patch('services.notifications.get_all_push_subscriptions')
    @patch('services.notifications.get_or_create_vapid_keys')
    @patch('services.notifications.webpush')
    def test_sends_to_all_subscribers(self, mock_webpush, mock_vapid, mock_subs):
        """Should send notification to every registered subscriber"""
        from services.notifications import send_push_notification

        mock_subs.return_value = [
            {'endpoint': 'https://push.example.com/1', 'p256dh': 'key1', 'auth': 'auth1'},
            {'endpoint': 'https://push.example.com/2', 'p256dh': 'key2', 'auth': 'auth2'},
        ]
        mock_vapid.return_value = ('public_key', 'private_key')

        sent = send_push_notification('Test Title', 'Test Body')

        assert sent == 2
        assert mock_webpush.call_count == 2

    @patch('services.notifications.get_all_push_subscriptions')
    def test_returns_zero_when_no_subscribers(self, mock_subs):
        """Should return 0 and not crash when no subscribers exist"""
        from services.notifications import send_push_notification

        mock_subs.return_value = []

        sent = send_push_notification('Test Title', 'Test Body')

        assert sent == 0

    @patch('services.notifications.get_all_push_subscriptions')
    @patch('services.notifications.get_or_create_vapid_keys')
    @patch('services.notifications.webpush')
    @patch('services.notifications.delete_push_subscription')
    def test_removes_expired_subscriptions_on_410_error(self, mock_delete, mock_webpush, mock_vapid, mock_subs):
        """Should delete subscription when push endpoint returns 410 Gone"""
        from services.notifications import send_push_notification
        from pywebpush import WebPushException

        mock_subs.return_value = [
            {'endpoint': 'https://push.example.com/expired', 'p256dh': 'key', 'auth': 'auth'},
        ]
        mock_vapid.return_value = ('public_key', 'private_key')

        # Simulate 410 Gone response (subscription expired)
        error_response = MagicMock()
        error_response.status_code = 410
        mock_webpush.side_effect = WebPushException('Gone', response=error_response)

        sent = send_push_notification('Test Title', 'Test Body')

        assert sent == 0
        mock_delete.assert_called_once_with('https://push.example.com/expired')


class TestNotifyPriceDrop:
    """Tests for price drop notification formatting"""

    @patch('services.notifications.send_push_notification')
    def test_formats_price_drop_notification_correctly(self, mock_send):
        """Should create notification with old and new prices in body"""
        from services.notifications import notify_price_drop

        mock_send.return_value = 1

        result = notify_price_drop(
            ad_title='Nintendo Switch',
            old_price='1.500,00',
            new_price='1.200,00',
            ad_url='https://olx.com.br/item-123',
            image_url='https://img.olx.com.br/image.jpg'
        )

        assert result == 1
        mock_send.assert_called_once()

        call_kwargs = mock_send.call_args.kwargs
        assert 'Preço baixou' in call_kwargs['title']
        assert '1.500,00' in call_kwargs['body']
        assert '1.200,00' in call_kwargs['body']
        assert call_kwargs['url'] == 'https://olx.com.br/item-123'


class TestNotifyCheapAd:
    """Tests for cheap ad notification formatting"""

    @patch('services.notifications.send_push_notification')
    def test_formats_cheap_ad_notification_correctly(self, mock_send):
        """Should create notification with price in title"""
        from services.notifications import notify_cheap_ad

        mock_send.return_value = 1

        result = notify_cheap_ad(
            ad_title='Jogo barato',
            price='50,00',
            ad_url='https://olx.com.br/item-123'
        )

        assert result == 1
        mock_send.assert_called_once()

        call_kwargs = mock_send.call_args.kwargs
        assert 'R$ 50,00' in call_kwargs['title']
        assert call_kwargs['url'] == 'https://olx.com.br/item-123'
