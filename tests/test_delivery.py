"""
Tests for delivery service - shipping quote functionality
"""

import pytest
from unittest.mock import patch, MagicMock
import httpx

from services.delivery import (
    DeliveryOption, DeliveryQuote,
    get_delivery_quote, get_delivery_quote_async
)


class TestDeliveryQuote:
    """Tests for DeliveryQuote dataclass"""

    def test_has_delivery_property(self):
        """Should return True when any option exists, False when empty"""
        quote_with_option = DeliveryQuote(
            standard=DeliveryOption('Padrão', 15.90, 'R$ 15,90', 5, False)
        )
        quote_empty = DeliveryQuote()

        assert quote_with_option.has_delivery is True
        assert quote_empty.has_delivery is False

    def test_cheapest_returns_cheaper_option(self):
        """Should return the cheaper option or None when empty"""
        # Standard is cheaper
        quote1 = DeliveryQuote(
            standard=DeliveryOption('Padrão', 15.90, 'R$ 15,90', 5, False),
            express=DeliveryOption('Expressa', 25.90, 'R$ 25,90', 2, False)
        )
        assert quote1.cheapest.name == 'Padrão'

        # Express is cheaper
        quote2 = DeliveryQuote(
            standard=DeliveryOption('Padrão', 20.00, 'R$ 20,00', 5, False),
            express=DeliveryOption('Expressa', 15.00, 'R$ 15,00', 2, False)
        )
        assert quote2.cheapest.name == 'Expressa'

        # Empty returns None
        quote3 = DeliveryQuote()
        assert quote3.cheapest is None


class TestGetDeliveryQuote:
    """Tests for sync delivery quote fetching"""

    @patch('services.delivery.get_setting')
    @patch('services.delivery.httpx.Client')
    def test_fetches_quote_with_both_options(self, mock_client_class, mock_setting):
        """Should parse API response with standard and express options"""
        mock_setting.return_value = '01310100'

        mock_response = MagicMock()
        mock_response.json.return_value = {
            'deliveryOptions': [
                {
                    'company': {'name': 'Padrão'},
                    'price': {'raw': 15.90, 'label': 'R$ 15,90'},
                    'dueDate': 5
                },
                {
                    'company': {'name': 'Expressa'},
                    'price': {'raw': 25.90, 'label': 'R$ 25,90'},
                    'dueDate': 2
                }
            ]
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        quote = get_delivery_quote(123456)

        assert quote is not None
        assert quote.standard is not None
        assert quote.standard.price == 15.90
        assert quote.express is not None
        assert quote.express.price == 25.90

    @patch('services.delivery.get_setting')
    @patch('services.delivery.httpx.Client')
    def test_uses_provided_zipcode(self, mock_client_class, mock_setting):
        """Should use provided zipcode instead of default"""
        mock_response = MagicMock()
        mock_response.json.return_value = {'deliveryOptions': []}

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        get_delivery_quote(123456, zipcode='12345678')

        # Should not call get_setting when zipcode is provided
        mock_setting.assert_not_called()

        # Verify payload has correct zipcode
        call_args = mock_client.post.call_args
        assert call_args[1]['json']['zipCode'] == '12345678'

    @patch('services.delivery.get_setting')
    @patch('services.delivery.httpx.Client')
    def test_skips_retirar_option(self, mock_client_class, mock_setting):
        """Should skip 'Retirar' (pickup) option"""
        mock_setting.return_value = '01310100'

        mock_response = MagicMock()
        mock_response.json.return_value = {
            'deliveryOptions': [
                {
                    'company': {'name': 'Retirar'},
                    'price': {'raw': 0, 'label': 'Grátis'},
                    'dueDate': 0
                },
                {
                    'company': {'name': 'Padrão'},
                    'price': {'raw': 15.90, 'label': 'R$ 15,90'},
                    'dueDate': 5
                }
            ]
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        quote = get_delivery_quote(123456)

        assert quote.standard is not None
        assert quote.express is None  # Only Retirar and Padrão, no Expressa

    @patch('services.delivery.get_setting')
    @patch('services.delivery.httpx.Client')
    def test_returns_none_on_empty_options(self, mock_client_class, mock_setting):
        """Should return None when no delivery options available"""
        mock_setting.return_value = '01310100'

        mock_response = MagicMock()
        mock_response.json.return_value = {'deliveryOptions': []}

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        quote = get_delivery_quote(123456)

        assert quote is None

    @patch('services.delivery.get_setting')
    @patch('services.delivery.httpx.Client')
    def test_returns_none_on_http_error(self, mock_client_class, mock_setting):
        """Should return None when API request fails"""
        mock_setting.return_value = '01310100'

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = httpx.HTTPError("Connection failed")
        mock_client_class.return_value = mock_client

        quote = get_delivery_quote(123456)

        assert quote is None

    @patch('services.delivery.get_setting')
    @patch('services.delivery.httpx.Client')
    def test_detects_free_delivery(self, mock_client_class, mock_setting):
        """Should mark option as free when price is 0"""
        mock_setting.return_value = '01310100'

        mock_response = MagicMock()
        mock_response.json.return_value = {
            'deliveryOptions': [
                {
                    'company': {'name': 'Padrão'},
                    'price': {'raw': 0, 'label': 'Grátis'},
                    'dueDate': 7
                }
            ]
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        quote = get_delivery_quote(123456)

        assert quote.standard.is_free is True


class TestGetDeliveryQuoteAsync:
    """Tests for async delivery quote fetching"""

    @pytest.mark.asyncio
    @patch('services.delivery.get_setting')
    async def test_fetches_quote_async(self, mock_setting):
        """Should fetch delivery quote asynchronously"""
        from unittest.mock import AsyncMock

        mock_setting.return_value = '01310100'

        mock_response = MagicMock()
        mock_response.json.return_value = {
            'deliveryOptions': [
                {
                    'company': {'name': 'Padrão'},
                    'price': {'raw': 15.90, 'label': 'R$ 15,90'},
                    'dueDate': 5
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch('services.delivery.httpx.AsyncClient', return_value=mock_client):
            quote = await get_delivery_quote_async(123456)

        assert quote is not None
        assert quote.standard.price == 15.90

    @pytest.mark.asyncio
    @patch('services.delivery.get_setting')
    async def test_returns_none_on_async_error(self, mock_setting):
        """Should return None when async request fails"""
        from unittest.mock import AsyncMock

        mock_setting.return_value = '01310100'

        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=httpx.HTTPError("Connection failed"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch('services.delivery.httpx.AsyncClient', return_value=mock_client):
            quote = await get_delivery_quote_async(123456)

        assert quote is None
