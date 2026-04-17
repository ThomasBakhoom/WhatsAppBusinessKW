"""Tests for phone number utility functions."""

import pytest
from app.utils.phone import normalize_phone, is_kuwaiti_number, format_display


class TestNormalizePhone:
    def test_kuwaiti_number_without_prefix(self):
        assert normalize_phone("99887766") == "+96599887766"

    def test_kuwaiti_number_with_country_code(self):
        assert normalize_phone("96599887766") == "+96599887766"

    def test_kuwaiti_number_with_plus(self):
        assert normalize_phone("+96599887766") == "+96599887766"

    def test_invalid_number_raises(self):
        with pytest.raises(ValueError):
            normalize_phone("123")


class TestIsKuwaitiNumber:
    def test_kuwaiti_number(self):
        assert is_kuwaiti_number("+96599887766") is True

    def test_non_kuwaiti_number(self):
        assert is_kuwaiti_number("+14155551234") is False

    def test_invalid_input(self):
        assert is_kuwaiti_number("abc") is False


class TestFormatDisplay:
    def test_kuwaiti_number(self):
        result = format_display("+96599887766")
        assert "+965" in result
