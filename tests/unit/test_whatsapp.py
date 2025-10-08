"""Tests for WhatsApp webhook integration."""

import pytest
from src.api.whatsapp import extract_phone_number


def test_extract_phone_number_with_prefix():
    """Test extracting phone number from Twilio format with prefix."""
    result = extract_phone_number("whatsapp:+14155238886")
    assert result == "+14155238886"


def test_extract_phone_number_without_prefix():
    """Test extracting phone number when prefix is missing."""
    result = extract_phone_number("+14155238886")
    assert result == "+14155238886"


def test_extract_phone_number_with_country_code():
    """Test extracting various phone number formats."""
    assert extract_phone_number("whatsapp:+1234567890") == "+1234567890"
    assert extract_phone_number("whatsapp:+442071234567") == "+442071234567"


def test_extract_phone_number_empty():
    """Test handling empty string."""
    result = extract_phone_number("")
    assert result == ""
