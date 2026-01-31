from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
import json


@dataclass
class Search:
    id: Optional[int] = None
    name: str = ""
    base_url: str = ""
    queries: list = field(default_factory=list)
    categories: list = field(default_factory=list)
    exclude_keywords: list = field(default_factory=list)
    active: bool = True
    created_at: Optional[str] = None
    state: str = ""
    region: str = ""
    category: str = "games"
    subcategory: str = ""
    cheap_threshold: Optional[float] = None  # Preço máximo para notificar como "barato"

    @classmethod
    def from_dict(cls, data: dict) -> "Search":
        return cls(
            id=data.get("id"),
            name=data.get("name", ""),
            base_url=data.get("base_url", ""),
            queries=json.loads(data.get("queries", "[]")) if isinstance(data.get("queries"), str) else data.get("queries", []),
            categories=json.loads(data.get("categories", "[]")) if isinstance(data.get("categories"), str) else data.get("categories", []),
            exclude_keywords=json.loads(data.get("exclude_keywords", "[]")) if isinstance(data.get("exclude_keywords"), str) else data.get("exclude_keywords", []),
            active=bool(data.get("active", True)),
            created_at=data.get("created_at"),
            state=data.get("state", ""),
            region=data.get("region", ""),
            category=data.get("category", "games"),
            subcategory=data.get("subcategory", ""),
            cheap_threshold=data.get("cheap_threshold")
        )


@dataclass
class Ad:
    id: Optional[int] = None
    url: str = ""
    title: str = ""
    price: str = ""
    description: str = ""
    state: str = ""
    municipality: str = ""
    neighbourhood: str = ""
    zipcode: str = ""
    seller: str = ""
    condition: str = ""
    published_at: str = ""
    main_category: str = ""
    sub_category: str = ""
    hobbie_type: str = ""
    images: list = field(default_factory=list)
    olx_pay: bool = False
    olx_delivery: bool = False
    search_id: Optional[int] = None
    found_at: Optional[str] = None
    deactivated_at: Optional[str] = None
    seen: bool = False
    watching: bool = False
    status: str = "active"
    cheap_threshold: Optional[float] = None  # Threshold da busca que encontrou o anúncio

    @classmethod
    def from_dict(cls, data: dict) -> "Ad":
        images = data.get("images", [])
        if isinstance(images, str):
            images = json.loads(images) if images else []

        return cls(
            id=data.get("id"),
            url=data.get("url", ""),
            title=data.get("title", ""),
            price=data.get("price", ""),
            description=data.get("description", ""),
            state=data.get("state", ""),
            municipality=data.get("municipality", ""),
            neighbourhood=data.get("neighbourhood", ""),
            zipcode=data.get("zipcode", ""),
            seller=data.get("seller", ""),
            condition=data.get("condition", ""),
            published_at=data.get("published_at", ""),
            main_category=data.get("main_category", ""),
            sub_category=data.get("sub_category", ""),
            hobbie_type=data.get("hobbie_type", ""),
            images=images,
            olx_pay=bool(data.get("olx_pay", False)),
            olx_delivery=bool(data.get("olx_delivery", False)),
            search_id=data.get("search_id"),
            found_at=data.get("found_at"),
            deactivated_at=data.get("deactivated_at"),
            seen=bool(data.get("seen", False)),
            watching=bool(data.get("watching", False)),
            status=data.get("status", "active"),
            cheap_threshold=data.get("cheap_threshold")
        )

    @property
    def is_cheap(self) -> bool:
        """Verifica se o preço está abaixo do threshold da busca"""
        if not self.cheap_threshold:
            return False
        try:
            price = parse_price_to_float(self.price)
            return price <= self.cheap_threshold
        except:
            return False

    @property
    def location(self) -> str:
        parts = []
        if self.neighbourhood:
            parts.append(self.neighbourhood)
        if self.municipality:
            parts.append(self.municipality)
        if self.state:
            parts.append(self.state.replace("#", ""))
        return ", ".join(parts)

    @property
    def first_image(self) -> Optional[str]:
        """Retorna primeira imagem (local se disponível, senão original)"""
        imgs = self.get_images()
        return imgs[0] if imgs else None

    def get_images(self) -> list[str]:
        """Retorna imagens locais se disponíveis, senão as originais"""
        if self.id and self.watching:
            from services.images import get_local_images
            local = get_local_images(self.id)
            if local:
                return local
        return self.images

    @property
    def formatted_date(self) -> str:
        if not self.published_at:
            return ""
        try:
            dt = datetime.strptime(self.published_at, "%Y-%m-%d %H:%M:%S")
            ts_correto = int(dt.timestamp()) * 1_000_000
            data_corrigida = datetime.fromtimestamp(ts_correto / 1000)
            return data_corrigida.strftime("%d/%m/%Y às %H:%M")
        except:
            return self.published_at

    @property
    def found_at_formatted(self) -> str:
        """Formata a data de quando o anúncio foi encontrado (converte UTC para local)"""
        if not self.found_at:
            return ""
        try:
            from datetime import timezone
            dt_utc = datetime.strptime(self.found_at, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            dt_local = dt_utc.astimezone()
            return dt_local.strftime("%d/%m %H:%M")
        except:
            return self.found_at

    @property
    def deactivated_at_formatted(self) -> str:
        """Formata a data de quando o anúncio ficou inativo (converte UTC para local)"""
        if not self.deactivated_at:
            return ""
        try:
            from datetime import timezone
            dt_utc = datetime.strptime(self.deactivated_at, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            dt_local = dt_utc.astimezone()
            return dt_local.strftime("%d/%m %H:%M")
        except:
            return self.deactivated_at

    @property
    def category_path(self) -> str:
        parts = []
        if self.main_category:
            parts.append(self.main_category)
        if self.sub_category:
            parts.append(self.sub_category)
        if self.hobbie_type:
            parts.append(self.hobbie_type)
        return " > ".join(parts)


@dataclass
class PriceHistory:
    id: Optional[int] = None
    ad_id: int = 0
    price: str = ""
    checked_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "PriceHistory":
        return cls(
            id=data.get("id"),
            ad_id=data.get("ad_id", 0),
            price=data.get("price", ""),
            checked_at=data.get("checked_at")
        )


def parse_price_to_float(price_str: str) -> float:
    if not price_str:
        return 0.0
    try:
        cleaned = price_str.replace(".", "").replace(",", ".").strip()
        return float(cleaned)
    except:
        return 0.0


def calculate_price_variation(history: list[PriceHistory]) -> tuple[float, str]:
    if len(history) < 2:
        return 0.0, "0%"

    first_price = parse_price_to_float(history[0].price)
    last_price = parse_price_to_float(history[-1].price)

    if first_price == 0:
        return 0.0, "0%"

    variation = ((last_price - first_price) / first_price) * 100
    sign = "+" if variation > 0 else ""
    return variation, f"{sign}{variation:.0f}%"
