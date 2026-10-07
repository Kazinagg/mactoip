import pytest
from mactoip.utils import normalize_mac

def test_normalize_mac_standard():
    assert normalize_mac("00:1A:2B:3C:4D:5E") == "00:1A:2B:3C:4D:5E"
    assert normalize_mac("00:1a:2b:3c:4d:5e") == "00:1A:2B:3C:4D:5E"

def test_normalize_mac_hyphens():
    assert normalize_mac("00-1A-2B-3C-4D-5E") == "00:1A:2B:3C:4D:5E"
    assert normalize_mac("00-1a-2b-3c-4d-5e") == "00:1A:2B:3C:4D:5E"

def test_normalize_mac_dots_cisco_style():
    assert normalize_mac("001a.2b3c.4d5e") == "00:1A:2B:3C:4D:5E"

def test_normalize_mac_raw_hex():
    assert normalize_mac("001A2B3C4D5E") == "00:1A:2B:3C:4D:5E"

def test_normalize_mac_invalid_length():
    with pytest.raises(ValueError, match="Некорректная длина MAC-адреса"):
        normalize_mac("00:1A:2B")

    with pytest.raises(ValueError, match="Некорректная длина MAC-адреса"):
        normalize_mac("00:1A:2B:3C:4D:5E:6F")

def test_normalize_mac_invalid_characters():
    with pytest.raises(ValueError, match="Некорректная длина MAC-адреса"):
        normalize_mac("ZZ:1A:2B:3C:4D:5E")

def test_normalize_mac_empty():
    with pytest.raises(ValueError, match="MAC-адрес не может быть пустым"):
        normalize_mac("")
