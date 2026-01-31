"""
Tests for input validation functions
"""

import pytest
from services.validators import (
    validate_olx_url,
    validate_zipcode,
    validate_search_name,
    validate_price_alert,
    ValidationError
)


class TestValidateOlxUrl:
    """Tests for OLX URL validation"""

    @pytest.mark.parametrize("url", [
        'https://www.olx.com.br/sao-paulo/games',
        'https://olx.com.br/brasil/games',
        'https://sp.olx.com.br/sao-paulo/games/nintendo-123',
        'https://rj.olx.com.br/rio-de-janeiro/eletronicos',
        'http://olx.com.br/brasil/games',
    ])
    def test_valid_urls_are_accepted(self, url):
        """Should accept valid OLX URLs from different states and paths"""
        assert validate_olx_url(url) is True

    @pytest.mark.parametrize("url,error_match", [
        ('https://google.com/search', 'olx.com.br'),
        ('https://fake-olx.com.br/games', 'olx.com.br'),
        ('ftp://olx.com.br/games', 'http'),
        ('', 'obrigatória'),
        (None, 'obrigatória'),
        ('https://olx.com.br/', 'caminho'),
    ])
    def test_invalid_urls_raise_validation_error(self, url, error_match):
        """Should reject invalid URLs with appropriate error messages"""
        with pytest.raises(ValidationError, match=error_match):
            validate_olx_url(url)


class TestValidateZipcode:
    """Tests for Brazilian CEP validation"""

    @pytest.mark.parametrize("cep", [
        '01310100',
        '01310-100',
        '01310 100',
        '12345678',
        '99999999',
    ])
    def test_valid_ceps_are_accepted(self, cep):
        """Should accept CEPs with or without formatting"""
        assert validate_zipcode(cep) is True

    @pytest.mark.parametrize("cep,error_match", [
        ('1234567', '8 números'),      # too short
        ('123456789', '8 números'),    # too long
        ('1234567a', '8 números'),     # has letter
        ('', 'obrigatório'),
        ('abcdefgh', '8 números'),     # all letters
    ])
    def test_invalid_ceps_raise_validation_error(self, cep, error_match):
        """Should reject invalid CEPs with appropriate error messages"""
        with pytest.raises(ValidationError, match=error_match):
            validate_zipcode(cep)


class TestValidateSearchName:
    """Tests for search name validation"""

    @pytest.mark.parametrize("name", [
        'Nintendo Switch',
        'A',
        'x' * 100,
        'Busca com números 123',
    ])
    def test_valid_names_are_accepted(self, name):
        """Should accept valid search names"""
        assert validate_search_name(name) is True

    @pytest.mark.parametrize("name,error_match", [
        ('', 'obrigatório'),
        ('   ', 'obrigatório'),
        ('x' * 101, '100 caracteres'),
    ])
    def test_invalid_names_raise_validation_error(self, name, error_match):
        """Should reject invalid names with appropriate error messages"""
        with pytest.raises(ValidationError, match=error_match):
            validate_search_name(name)


class TestValidatePriceAlert:
    """Tests for price alert validation and parsing"""

    @pytest.mark.parametrize("price_str,expected", [
        ('100', 100.0),
        ('100,50', 100.50),
        ('1.500,00', 1500.00),
        ('10.000', 10000.0),
        (' 500 ', 500.0),
        ('1.234.567,89', 1234567.89),
    ])
    def test_valid_prices_are_parsed_correctly(self, price_str, expected):
        """Should parse Brazilian price formats to float"""
        assert validate_price_alert(price_str) == expected

    @pytest.mark.parametrize("price_str,error_match", [
        ('abc', 'inválido'),
        ('', 'obrigatório'),
        ('0', 'maior que zero'),
        ('-100', 'maior que zero'),
        ('99999999', 'muito alto'),
    ])
    def test_invalid_prices_raise_validation_error(self, price_str, error_match):
        """Should reject invalid prices with appropriate error messages"""
        with pytest.raises(ValidationError, match=error_match):
            validate_price_alert(price_str)
