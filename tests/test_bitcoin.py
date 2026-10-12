"""Regression coverage for selectable ticker logos."""
import io

import pytest
import homeassistant  # Initialize Home Assistant's validation compatibility layer.
import voluptuous as vol
from PIL import Image

from custom_components.idotmatrix import bitcoin
from custom_components.idotmatrix.service_validation import service_schema


@pytest.mark.parametrize("logo", ["ethereum.png", "bitcoin_logo.png", ""])
def test_bitcoin_service_accepts_logo(logo):
    payload = {"price_entity": "sensor.token_price", "logo": logo}
    assert service_schema("show_bitcoin")(payload) == payload


def test_bitcoin_service_keeps_logo_optional():
    payload = {"price_entity": "sensor.bitcoin_price"}
    assert service_schema("show_bitcoin")(payload) == payload
    with pytest.raises(vol.Invalid):
        service_schema("show_weather")({"logo": "ethereum.png"})


@pytest.mark.parametrize("logo", [None, [], "x" * 129])
def test_bitcoin_service_rejects_invalid_logo(logo):
    with pytest.raises(vol.Invalid):
        service_schema("show_bitcoin")({"logo": logo})


@pytest.fixture
def logo_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(bitcoin, "_IMAGES_DIR", str(tmp_path))
    bitcoin._logo.cache_clear()
    Image.new("RGBA", (20, 20), (0, 255, 0, 255)).save(tmp_path / "ethereum.png")
    Image.new("RGBA", (20, 20), (255, 0, 0, 255)).save(tmp_path / "bitcoin_logo.png")
    yield tmp_path
    bitcoin._logo.cache_clear()


@pytest.mark.parametrize("size", [32, 64])
@pytest.mark.parametrize("filename,expected", [("ethereum.png", (0, 255, 0)), (None, (255, 0, 0)), ("", (255, 0, 0))])
def test_ticker_renders_selected_or_default_logo(logo_directory, size, filename, expected):
    data = bitcoin.TickerData(60000, logo_filename=filename)
    with Image.open(io.BytesIO(bitcoin.render_bitcoin_gif(data, size))) as image:
        assert image.size == (size, size)
        assert image.convert("RGB").getpixel((size // 2, 5)) == expected


def test_missing_logo_uses_fallback(logo_directory):
    assert bitcoin._logo(15, "missing.png").tobytes() == bitcoin._fallback_logo(15).tobytes()


def test_logo_change_invalidates_ticker_signature():
    assert bitcoin.TickerData(60000, logo_filename="bitcoin_logo.png").signature() != bitcoin.TickerData(60000, logo_filename="ethereum.png").signature()
