"""
Tests for OLX scraper - parsing and async HTTP operations
"""

import pytest
from aioresponses import aioresponses

from services.scraper import OlxScraper, filter_urls_by_keywords


class TestOlxScraperUrlParsing:
    """Tests for URL extraction from OLX search pages"""

    def test_extracts_valid_olx_ad_urls(self, sample_olx_search_html):
        """Should extract only valid OLX ad URLs, excluding non-OLX links"""
        scraper = OlxScraper()
        urls = scraper._parse_ad_urls(sample_olx_search_html, [])

        # Should find exactly 3 OLX ads
        assert len(urls) == 3

        # All URLs should be OLX ads with numeric IDs
        for url in urls:
            assert 'olx.com.br' in url
            assert any(char.isdigit() for char in url)

        # Should NOT include non-OLX URLs
        assert not any('google.com' in url for url in urls)

    def test_filters_urls_by_category_pattern(self, sample_olx_search_html):
        """Should return only URLs matching category pattern"""
        scraper = OlxScraper()

        # Filter for 'nintendo' only
        urls = scraper._parse_ad_urls(sample_olx_search_html, ['nintendo'])

        assert len(urls) == 1
        assert 'nintendo-switch' in urls[0]
        assert 'ps5' not in urls[0]
        assert 'xbox' not in urls[0]


class TestOlxScraperAdParsing:
    """Tests for ad info extraction from OLX ad pages"""

    def test_extracts_complete_ad_info_from_html(self, sample_olx_ad_html):
        """Should parse all ad fields from OLX page HTML"""
        scraper = OlxScraper()
        ad = scraper._parse_ad_info(
            'https://sp.olx.com.br/sao-paulo/games/nintendo-123',
            sample_olx_ad_html
        )

        assert ad is not None

        # Core fields
        assert ad.title == 'Nintendo Switch Completo'
        assert ad.price == '1.500,00'

        # Location
        assert ad.state == '#SP'
        assert ad.municipality == 'São Paulo'

        # Seller
        assert ad.seller == 'João Silva'

        # Images
        assert len(ad.images) == 2
        assert all('img.olx.com.br' in img for img in ad.images)

    def test_returns_none_for_inactive_ad(self, sample_olx_inactive_html):
        """Should return None when ad page shows 'not found' message"""
        scraper = OlxScraper()
        ad = scraper._parse_ad_info(
            'https://sp.olx.com.br/sao-paulo/games/nintendo-123',
            sample_olx_inactive_html
        )

        assert ad is None

    def test_extracts_price_from_data_layer(self, sample_olx_ad_html):
        """Should extract price from JavaScript dataLayer"""
        scraper = OlxScraper()
        price = scraper._parse_price(sample_olx_ad_html)

        assert price == '1.500,00'


class TestOlxScraperBuildUrl:
    """Tests for search URL construction"""

    @pytest.mark.parametrize("base_url,query,expected_contains", [
        # With query
        ('https://sp.olx.com.br/games', 'nintendo switch', ['q=nintendo%20switch', 'sf=1']),
        # Without query
        ('https://sp.olx.com.br/games', '', ['sf=1']),
        # With existing params
        ('https://sp.olx.com.br/games?pe=500', 'nintendo', ['pe=500', 'q=nintendo', 'sf=1']),
    ])
    def test_builds_search_url_correctly(self, base_url, query, expected_contains):
        """Should build search URL with query params and sf=1 flag"""
        scraper = OlxScraper()
        url = scraper.build_search_url(base_url, query)

        for expected in expected_contains:
            assert expected in url

    def test_url_without_query_has_no_q_param(self):
        """Should not include q= parameter when query is empty"""
        scraper = OlxScraper()
        url = scraper.build_search_url('https://sp.olx.com.br/games', '')

        assert 'q=' not in url


class TestOlxScraperAsync:
    """Tests for async HTTP operations with mocked responses"""

    @pytest.mark.asyncio
    async def test_fetches_and_parses_search_results(self, sample_olx_search_html):
        """Should fetch search page and extract ad URLs"""
        scraper = OlxScraper()
        search_url = 'https://sp.olx.com.br/sao-paulo/games?sf=1'

        with aioresponses() as m:
            m.get(search_url, body=sample_olx_search_html)
            urls = await scraper.get_ad_urls_async(search_url, [])

            assert len(urls) == 3

        await scraper.close()

    @pytest.mark.asyncio
    async def test_fetches_and_parses_ad_info(self, sample_olx_ad_html):
        """Should fetch ad page and extract ad details"""
        scraper = OlxScraper()
        url = 'https://sp.olx.com.br/sao-paulo/games/nintendo-123'

        with aioresponses() as m:
            m.get(url, body=sample_olx_ad_html)
            ad = await scraper.get_ad_info_async(url)

            assert ad is not None
            assert ad.title == 'Nintendo Switch Completo'
            assert ad.price == '1.500,00'

        await scraper.close()

    @pytest.mark.asyncio
    async def test_fetches_current_price(self, sample_olx_ad_html):
        """Should fetch and extract only the price from ad page"""
        scraper = OlxScraper()
        url = 'https://sp.olx.com.br/sao-paulo/games/nintendo-123'

        with aioresponses() as m:
            m.get(url, body=sample_olx_ad_html)
            price = await scraper.get_current_price_async(url)

            assert price == '1.500,00'

        await scraper.close()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("response_body,status_code,expected_status", [
        (b'<html><body>Active ad</body></html>', 200, 'active'),
        ('Página não foi encontrada'.encode('utf-8'), 200, 'inactive'),
        (b'', 404, 'inactive'),
        (b'', 410, 'inactive'),
    ])
    async def test_detects_ad_status_correctly(self, response_body, status_code, expected_status):
        """Should detect if ad is active or inactive based on response"""
        scraper = OlxScraper()
        url = 'https://sp.olx.com.br/sao-paulo/games/nintendo-123'

        with aioresponses() as m:
            m.get(url, body=response_body, status=status_code)
            status = await scraper.check_ad_status_async(url)

            assert status == expected_status

        await scraper.close()


class TestFilterUrlsByKeywords:
    """Tests for URL exclusion filter"""

    def test_excludes_urls_containing_keywords(self):
        """Should remove URLs that contain any exclude keyword"""
        urls = [
            'https://olx.com.br/nintendo-switch-123',
            'https://olx.com.br/nintendo-switch-lite-456',
            'https://olx.com.br/ps5-789',
            'https://olx.com.br/switch-broken-999',
        ]

        filtered = filter_urls_by_keywords(urls, ['lite', 'broken'])

        assert len(filtered) == 2
        assert 'https://olx.com.br/nintendo-switch-123' in filtered
        assert 'https://olx.com.br/ps5-789' in filtered

        # Excluded URLs should not be present
        assert not any('lite' in url for url in filtered)
        assert not any('broken' in url for url in filtered)

    def test_filter_is_case_insensitive(self):
        """Should match keywords regardless of case"""
        urls = ['https://olx.com.br/Nintendo-Switch-LITE-123']

        filtered = filter_urls_by_keywords(urls, ['lite'])

        assert len(filtered) == 0
