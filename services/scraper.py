import aiohttp
import asyncio
import requests
import re
import json
import functools
import random
from bs4 import BeautifulSoup
from typing import Optional, Callable, TypeVar
from models import Ad
from services.logger import get_logger
from services.exceptions import NetworkError, ParseError, RateLimitError, AdNotFoundError

logger = get_logger("olx_monitor.scraper")

# User-Agents realistas de browsers populares
USER_AGENTS = [
    # Chrome Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    # Chrome Mac
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    # Firefox Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
    # Firefox Mac
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14.3; rv:122.0) Gecko/20100101 Firefox/122.0',
    # Safari Mac
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    # Edge Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
]

T = TypeVar('T')


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    exceptions: tuple = (NetworkError, aiohttp.ClientError, requests.RequestException)
):
    """
    Decorator for retry with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds (doubles each retry)
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
            logger.error(f"All {max_retries} attempts failed. Last error: {last_exception}")
            raise last_exception

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            import time
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
            logger.error(f"All {max_retries} attempts failed. Last error: {last_exception}")
            raise last_exception

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


class OlxScraper:
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        self._rotate_headers()

    def _rotate_headers(self):
        """Gera headers realistas com User-Agent aleatório"""
        user_agent = random.choice(USER_AGENTS)
        self.headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.olx.com.br/',
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session with connection pooling"""
        if self._session is None or self._session.closed:
            # Rotacionar headers a cada nova sessão
            self._rotate_headers()
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(
                headers=self.headers,
                connector=connector,
                timeout=timeout,
                cookie_jar=aiohttp.CookieJar()
            )
        return self._session

    async def close(self):
        """Close the aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    def build_search_url(self, base_url: str, query: str) -> str:
        if query:
            query_encoded = query.replace(' ', '%20')
            if '?' in base_url:
                return f"{base_url}&q={query_encoded}&sf=1"
            else:
                return f"{base_url}?q={query_encoded}&sf=1"
        else:
            if '?' in base_url:
                return f"{base_url}&sf=1"
            else:
                return f"{base_url}?sf=1"

    # ==================== SYNC METHODS (for backward compatibility) ====================

    def get_ad_urls(self, search_url: str, category_patterns: list[str]) -> list[str]:
        try:
            response = requests.get(search_url, headers=self.headers, timeout=30)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch search URL: status {response.status_code}")
                return []

            return self._parse_ad_urls(response.content, category_patterns)
        except requests.Timeout as e:
            logger.error(f"Timeout fetching search URL {search_url}: {e}")
            return []
        except requests.RequestException as e:
            logger.error(f"Network error fetching URLs: {e}")
            return []
        except Exception as e:
            logger.exception(f"Unexpected error fetching URLs: {e}")
            return []

    def get_ad_info(self, url: str) -> Optional[Ad]:
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            return self._parse_ad_info(url, response.content)
        except requests.Timeout as e:
            logger.error(f"Timeout fetching ad {url}: {e}")
            return None
        except requests.RequestException as e:
            logger.error(f"Network error fetching ad {url}: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error fetching ad {url}: {e}")
            return None

    def get_current_price(self, url: str) -> Optional[str]:
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            return self._parse_price(response.content)
        except requests.Timeout as e:
            logger.error(f"Timeout checking price {url}: {e}")
            return None
        except requests.RequestException as e:
            logger.error(f"Network error checking price {url}: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error checking price {url}: {e}")
            return None

    def check_ad_status(self, url: str) -> Optional[str]:
        """
        Check if an ad is still active.
        Returns: 'active', 'inactive', or None (don't change status)
        """
        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=30,
                allow_redirects=True
            )

            if response.status_code == 200:
                content_lower = response.text.lower()
                if 'não encontrado' in content_lower or 'página não foi encontrada' in content_lower:
                    return 'inactive'
                return 'active'
            elif response.status_code in (404, 410):
                return 'inactive'
            elif response.status_code in (401, 403):
                logger.warning(f"Rate limited ({response.status_code}) for {url}")
                return None
            elif response.status_code >= 500:
                logger.warning(f"Server error ({response.status_code}) for {url}")
                return None
            else:
                logger.warning(f"Unexpected status {response.status_code} for {url}")
                return None

        except requests.Timeout:
            logger.error(f"Timeout checking status {url}")
            return None
        except requests.RequestException as e:
            logger.error(f"Network error checking status {url}: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error checking status {url}: {e}")
            return None

    # ==================== ASYNC METHODS ====================

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    async def get_ad_urls_async(self, search_url: str, category_patterns: list[str]) -> list[str]:
        """Async version of get_ad_urls with retry"""
        try:
            session = await self._get_session()
            async with session.get(search_url) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch search URL: status {response.status}")
                    return []
                content = await response.read()
                return self._parse_ad_urls(content, category_patterns)
        except asyncio.TimeoutError as e:
            logger.error(f"Timeout fetching search URL {search_url}")
            raise NetworkError(f"Timeout: {e}") from e
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching URLs: {e}")
            raise NetworkError(str(e)) from e

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    async def get_ad_info_async(self, url: str) -> Optional[Ad]:
        """Async version of get_ad_info with retry"""
        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status in (404, 410):
                    raise AdNotFoundError(f"Ad not found: {url}")
                if response.status in (401, 403):
                    raise RateLimitError(f"Rate limited: {response.status}")
                content = await response.read()
                return self._parse_ad_info(url, content)
        except asyncio.TimeoutError as e:
            logger.error(f"Timeout fetching ad {url}")
            raise NetworkError(f"Timeout: {e}") from e
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching ad {url}: {e}")
            raise NetworkError(str(e)) from e

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    async def get_current_price_async(self, url: str) -> Optional[str]:
        """Async version of get_current_price with retry"""
        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status in (404, 410):
                    raise AdNotFoundError(f"Ad not found: {url}")
                content = await response.read()
                return self._parse_price(content)
        except asyncio.TimeoutError as e:
            logger.error(f"Timeout checking price {url}")
            raise NetworkError(f"Timeout: {e}") from e
        except aiohttp.ClientError as e:
            logger.error(f"Network error checking price {url}: {e}")
            raise NetworkError(str(e)) from e

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    async def check_ad_status_async(self, url: str) -> Optional[str]:
        """Async version of check_ad_status with retry"""
        try:
            session = await self._get_session()
            async with session.get(url, allow_redirects=True) as response:
                if response.status == 200:
                    text = await response.text()
                    content_lower = text.lower()
                    if 'não encontrado' in content_lower or 'página não foi encontrada' in content_lower:
                        return 'inactive'
                    return 'active'
                elif response.status in (404, 410):
                    return 'inactive'
                elif response.status in (401, 403):
                    logger.warning(f"Rate limited ({response.status}) for {url}")
                    raise RateLimitError(f"Rate limited: {response.status}")
                elif response.status >= 500:
                    logger.warning(f"Server error ({response.status}) for {url}")
                    raise NetworkError(f"Server error: {response.status}")
                else:
                    logger.warning(f"Unexpected status {response.status} for {url}")
                    return None
        except asyncio.TimeoutError as e:
            logger.error(f"Timeout checking status {url}")
            raise NetworkError(f"Timeout: {e}") from e
        except aiohttp.ClientError as e:
            logger.error(f"Network error checking status {url}: {e}")
            raise NetworkError(str(e)) from e

    # ==================== PARSING HELPERS ====================

    def _parse_ad_urls(self, content: bytes, category_patterns: list[str]) -> list[str]:
        """Parse ad URLs from search page content"""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            links = soup.find_all('a', href=True)
            urls = []

            for link in links:
                url = link['href']

                if not re.search(r"https:\/\/(?:[a-z]{2}\.)?olx\.com\.br\/[\w\-\/]+-\d+", url):
                    continue

                if not category_patterns:
                    urls.append(url)
                else:
                    for pattern in category_patterns:
                        if re.search(pattern, url):
                            urls.append(url)
                            break

            return list(set(urls))
        except Exception as e:
            logger.error(f"Error parsing ad URLs: {e}")
            raise ParseError(f"Failed to parse ad URLs: {e}") from e

    def _extract_json_data(self, soup, type_attr: str) -> dict:
        script = soup.find('script', type=type_attr)
        return json.loads(script.string) if script else {}

    def _extract_data_layer(self, soup) -> list:
        script_tag = soup.find('script', string=lambda s: s and 'window.dataLayer' in s)
        if script_tag:
            json_data = script_tag.string.strip()
            start = json_data.find('[')
            end = json_data.rfind(']') + 1
            return json.loads(json_data[start:end])
        return []

    def _parse_ad_info(self, url: str, content: bytes) -> Optional[Ad]:
        """Parse ad info from page content"""
        try:
            soup = BeautifulSoup(content, 'html.parser')

            json_ld_data = self._extract_json_data(soup, 'application/ld+json')
            description = json_ld_data.get("description", "").replace('<br>', '\n')
            images = [img.get('contentUrl') for img in json_ld_data.get("image", [])]

            data_layer = self._extract_data_layer(soup)
            if not data_layer:
                logger.debug(f"No data layer found for {url}")
                return None

            ad_detail = data_layer[0].get('page', {}).get('detail', {})
            ad_info = data_layer[0].get('page', {}).get('adDetail', {})

            title = ad_info.get("subject", "").replace('<br>', '')
            price = ad_detail.get("price", "")

            if not price or "página não foi encontrada" in str(price).lower():
                logger.debug(f"Ad not found or invalid price for {url}")
                return None

            state = ad_info.get("state", "")
            if state:
                state = f"#{state}"

            neighbourhood = ad_info.get("neighbourhood", "")
            if neighbourhood:
                neighbourhood = f"{neighbourhood},"

            olx_pay_data = ad_detail.get("olxPay", {})
            olx_delivery_data = ad_detail.get("olxDelivery", {})

            return Ad(
                url=url,
                title=title,
                price=price,
                description=description,
                state=state,
                municipality=ad_info.get("municipality", ""),
                neighbourhood=neighbourhood.rstrip(","),
                zipcode=ad_detail.get("zipcode", ""),
                seller=ad_info.get("sellerName", ""),
                condition=ad_info.get("hobbies_condition", ""),
                published_at=ad_info.get("adDate", ""),
                main_category=ad_info.get("mainCategory", ""),
                sub_category=ad_info.get("subCategory", ""),
                hobbie_type=ad_info.get("hobbies_collections_type", ""),
                images=images,
                olx_pay=bool(olx_pay_data),
                olx_delivery=bool(olx_delivery_data.get("enabled", False))
            )
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing ad info for {url}: {e}")
            return None

    def _parse_price(self, content: bytes) -> Optional[str]:
        """Parse price from page content"""
        try:
            soup = BeautifulSoup(content, 'html.parser')

            data_layer = self._extract_data_layer(soup)
            if not data_layer:
                return None

            ad_detail = data_layer[0].get('page', {}).get('detail', {})
            price = ad_detail.get("price", "")

            if not price or "página não foi encontrada" in str(price).lower():
                return None

            return price
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing price: {e}")
            return None


def filter_urls_by_keywords(urls: list[str], exclude_keywords: list[str]) -> list[str]:
    return [
        url for url in urls
        if not any(keyword.lower() in url.lower() for keyword in exclude_keywords)
    ]
