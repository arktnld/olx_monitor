import requests
import re
import json
from bs4 import BeautifulSoup
from typing import Optional
from models import Ad


class OlxScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        }

    def build_search_url(self, base_url: str, query: str) -> str:
        if query:
            query_encoded = query.replace(' ', '%20')
            if '?' in base_url:
                return f"{base_url}&q={query_encoded}&sf=1"
            else:
                return f"{base_url}?q={query_encoded}&sf=1"
        else:
            # Sem query - apenas categoria
            if '?' in base_url:
                return f"{base_url}&sf=1"
            else:
                return f"{base_url}?sf=1"

    def get_ad_urls(self, search_url: str, category_patterns: list[str]) -> list[str]:
        try:
            response = requests.get(search_url, headers=self.headers, timeout=30)
            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.content, 'html.parser')
            links = soup.find_all('a', href=True)
            urls = []

            for link in links:
                url = link['href']

                if not re.search(r"https:\/\/(?:[a-z]{2}\.)?olx\.com\.br\/[\w\-\/]+-\d+", url):
                    continue

                # Se não há padrões de categoria, aceita todos os anúncios
                if not category_patterns:
                    urls.append(url)
                else:
                    # Filtra por categoria para remover anúncios patrocinados de outras categorias
                    for pattern in category_patterns:
                        if re.search(pattern, url):
                            urls.append(url)
                            break

            return list(set(urls))
        except Exception as e:
            print(f"Erro ao buscar URLs: {e}")
            return []

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

    def get_ad_info(self, url: str) -> Optional[Ad]:
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            soup = BeautifulSoup(response.content, 'html.parser')

            json_ld_data = self._extract_json_data(soup, 'application/ld+json')
            description = json_ld_data.get("description", "").replace('<br>', '\n')
            images = [img.get('contentUrl') for img in json_ld_data.get("image", [])]

            data_layer = self._extract_data_layer(soup)
            if not data_layer:
                return None

            ad_detail = data_layer[0].get('page', {}).get('detail', {})
            ad_info = data_layer[0].get('page', {}).get('adDetail', {})

            title = ad_info.get("subject", "").replace('<br>', '')
            price = ad_detail.get("price", "")

            if not price or "página não foi encontrada" in str(price).lower():
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

        except Exception as e:
            print(f"Erro ao obter info do anúncio {url}: {e}")
            return None

    def get_current_price(self, url: str) -> Optional[str]:
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            soup = BeautifulSoup(response.content, 'html.parser')

            data_layer = self._extract_data_layer(soup)
            if not data_layer:
                return None

            ad_detail = data_layer[0].get('page', {}).get('detail', {})
            price = ad_detail.get("price", "")

            if not price or "página não foi encontrada" in str(price).lower():
                return None

            return price
        except Exception as e:
            print(f"Erro ao verificar preço {url}: {e}")
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
                # Check if it's an error page (OLX sometimes returns 200 for error pages)
                content_lower = response.text.lower()
                if 'não encontrado' in content_lower or 'página não foi encontrada' in content_lower:
                    return 'inactive'
                return 'active'
            elif response.status_code in (404, 410):
                # 404 = not found, 410 = gone (permanently removed)
                return 'inactive'
            elif response.status_code in (401, 403):
                # 401/403 = auth/bot protection - don't change status
                print(f"{response.status_code} (proteção anti-bot) para {url}")
                return None
            elif response.status_code >= 500:
                # Server error, don't change status
                print(f"Erro do servidor OLX (status {response.status_code}) para {url}")
                return None
            else:
                # Unknown status code
                print(f"Status code inesperado {response.status_code} para {url}")
                return None

        except requests.Timeout:
            print(f"Timeout ao verificar {url}")
            return None
        except requests.RequestException as e:
            print(f"Erro de rede ao verificar {url}: {e}")
            return None
        except Exception as e:
            print(f"Erro inesperado ao verificar {url}: {e}")
            return None


def filter_urls_by_keywords(urls: list[str], exclude_keywords: list[str]) -> list[str]:
    return [
        url for url in urls
        if not any(keyword.lower() in url.lower() for keyword in exclude_keywords)
    ]
