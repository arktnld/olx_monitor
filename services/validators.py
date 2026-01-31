"""Input validation for OLX Monitor"""

import re
from urllib.parse import urlparse
from typing import Optional


class ValidationError(Exception):
    """Validation error with user-friendly message"""
    pass


def validate_olx_url(url: str) -> bool:
    """
    Validate that a URL is a valid OLX Brazil URL.

    Args:
        url: The URL to validate

    Returns:
        True if valid

    Raises:
        ValidationError: If URL is invalid
    """
    if not url or not isinstance(url, str):
        raise ValidationError("URL é obrigatória")

    url = url.strip()

    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception:
        raise ValidationError("URL inválida")

    # Validate scheme
    if parsed.scheme not in ('http', 'https'):
        raise ValidationError("URL deve começar com http:// ou https://")

    # Whitelist: only olx.com.br domains
    valid_domains = (
        'olx.com.br',
        'www.olx.com.br',
    )
    # Also allow state subdomains like sp.olx.com.br
    if not any(
        parsed.netloc == domain or parsed.netloc.endswith(f'.{domain}')
        for domain in valid_domains
    ):
        raise ValidationError("URL deve ser do domínio olx.com.br")

    # Validate path exists
    if not parsed.path or parsed.path == '/':
        raise ValidationError("URL deve conter um caminho válido")

    return True


def validate_zipcode(cep: str) -> bool:
    """
    Validate Brazilian CEP (postal code).

    Args:
        cep: The CEP to validate (with or without hyphen)

    Returns:
        True if valid

    Raises:
        ValidationError: If CEP is invalid
    """
    if not cep or not isinstance(cep, str):
        raise ValidationError("CEP é obrigatório")

    # Remove hyphen and spaces
    cep_clean = cep.replace('-', '').replace(' ', '').strip()

    # Must be exactly 8 digits
    if not re.match(r'^\d{8}$', cep_clean):
        raise ValidationError("CEP deve conter exatamente 8 números")

    # Basic range validation (Brazilian CEPs range from 01000-000 to 99999-999)
    cep_num = int(cep_clean)
    if cep_num < 1000000 or cep_num > 99999999:
        raise ValidationError("CEP fora do intervalo válido")

    return True


def sanitize_cep(cep: str) -> str:
    """
    Sanitize CEP input to digits only.

    Args:
        cep: The CEP to sanitize

    Returns:
        Sanitized CEP (8 digits only)
    """
    return cep.replace('-', '').replace(' ', '').strip()


def validate_search_name(name: str) -> bool:
    """
    Validate search name.

    Args:
        name: The search name to validate

    Returns:
        True if valid

    Raises:
        ValidationError: If name is invalid
    """
    if not name or not isinstance(name, str):
        raise ValidationError("Nome é obrigatório")

    name = name.strip()

    if len(name) < 1:
        raise ValidationError("Nome é obrigatório")

    if len(name) > 100:
        raise ValidationError("Nome deve ter no máximo 100 caracteres")

    return True


def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize text input by stripping and optionally truncating.

    Args:
        text: The text to sanitize
        max_length: Optional maximum length

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    text = text.strip()

    if max_length and len(text) > max_length:
        text = text[:max_length]

    return text


def validate_price_alert(target_price: str) -> float:
    """
    Validate and parse price alert target.

    Args:
        target_price: The target price string (e.g., "100" or "100,50")

    Returns:
        Parsed price as float

    Raises:
        ValidationError: If price is invalid
    """
    if not target_price or not isinstance(target_price, str):
        raise ValidationError("Preço alvo é obrigatório")

    # Clean the price string
    price_clean = target_price.strip().replace('.', '').replace(',', '.')

    try:
        price = float(price_clean)
    except ValueError:
        raise ValidationError("Preço inválido. Use formato: 100 ou 100,50")

    if price <= 0:
        raise ValidationError("Preço deve ser maior que zero")

    if price > 10000000:  # 10 million limit
        raise ValidationError("Preço muito alto")

    return price
