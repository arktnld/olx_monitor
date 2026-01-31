"""Serviço para consultar frete do OLX"""

import httpx
from typing import Optional
from dataclasses import dataclass
from services.database import get_setting

DELIVERY_API = "https://apigw.olx.com.br/delivery/quote"

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0",
    "Origin": "https://www.olx.com.br",
    "Referer": "https://www.olx.com.br/",
}


@dataclass
class DeliveryOption:
    name: str
    price: float
    price_label: str
    days: int
    is_free: bool


@dataclass
class DeliveryQuote:
    standard: Optional[DeliveryOption] = None
    express: Optional[DeliveryOption] = None

    @property
    def has_delivery(self) -> bool:
        return self.standard is not None or self.express is not None

    @property
    def cheapest(self) -> Optional[DeliveryOption]:
        if self.standard and self.express:
            return self.standard if self.standard.price <= self.express.price else self.express
        return self.standard or self.express


def get_delivery_quote(list_id: int, zipcode: Optional[str] = None) -> Optional[DeliveryQuote]:
    """
    Consulta o frete para um anúncio.

    Args:
        list_id: ID do anúncio (listId extraído da URL)
        zipcode: CEP de destino (se não informado, usa o da configuração)

    Returns:
        DeliveryQuote com as opções de frete ou None se não disponível
    """
    if zipcode is None:
        zipcode = get_setting('delivery_zipcode', '72860175')

    payload = {
        "zipCode": zipcode,
        "listId": list_id,
        "searchCategoryLevelZero": 16000,
        "searchCategoryLevelOne": 16040,
        "searchCategoryLevelTwo": None,
        "weight": 1.0
    }

    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(DELIVERY_API, json=payload, headers=HEADERS)
            response.raise_for_status()
            data = response.json()

            quote = DeliveryQuote()

            for opt in data.get('deliveryOptions', []):
                company_name = opt.get('company', {}).get('name', '')
                price_data = opt.get('price', {})
                price_raw = price_data.get('raw', 0)
                price_label = price_data.get('label', f'R$ {price_raw:.2f}')
                days = opt.get('dueDate', 0)
                is_free = price_raw == 0 and company_name != 'Retirar'

                if company_name == 'Retirar':
                    continue

                option = DeliveryOption(
                    name=company_name,
                    price=price_raw,
                    price_label=price_label,
                    days=days,
                    is_free=is_free
                )

                if company_name == 'Padrão':
                    quote.standard = option
                elif company_name == 'Expressa':
                    quote.express = option

            return quote if quote.has_delivery else None

    except Exception:
        return None


async def get_delivery_quote_async(list_id: int, zipcode: Optional[str] = None) -> Optional[DeliveryQuote]:
    """
    Versão assíncrona para consultar o frete.
    """
    if zipcode is None:
        zipcode = get_setting('delivery_zipcode', '72860175')

    payload = {
        "zipCode": zipcode,
        "listId": list_id,
        "searchCategoryLevelZero": 16000,
        "searchCategoryLevelOne": 16040,
        "searchCategoryLevelTwo": None,
        "weight": 1.0
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(DELIVERY_API, json=payload, headers=HEADERS)
            response.raise_for_status()
            data = response.json()

            quote = DeliveryQuote()

            for opt in data.get('deliveryOptions', []):
                company_name = opt.get('company', {}).get('name', '')
                price_data = opt.get('price', {})
                price_raw = price_data.get('raw', 0)
                price_label = price_data.get('label', f'R$ {price_raw:.2f}')
                days = opt.get('dueDate', 0)
                is_free = price_raw == 0 and company_name != 'Retirar'

                if company_name == 'Retirar':
                    continue

                option = DeliveryOption(
                    name=company_name,
                    price=price_raw,
                    price_label=price_label,
                    days=days,
                    is_free=is_free
                )

                if company_name == 'Padrão':
                    quote.standard = option
                elif company_name == 'Expressa':
                    quote.express = option

            return quote if quote.has_delivery else None

    except Exception:
        return None
