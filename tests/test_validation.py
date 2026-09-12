import io
import json
from pathlib import Path

import pytest
import voluptuous as vol
from PIL import Image

from custom_components.idotmatrix.service_validation import service_schema
from custom_components.idotmatrix.weather import WeatherData, render_weather_gif
from custom_components.idotmatrix.message import MessageSpec, render_message_gif


@pytest.mark.parametrize("interval", [-1, 0, 256, 300])
def test_invalid_carousel_interval(interval):
    with pytest.raises(vol.Invalid):
        service_schema("display_gif")({"path": "/media/test.gif", "rotation_interval": interval})


def test_selector_values_and_required_sensors():
    assert service_schema("show_clock")({"pixel_size": "32", "face": "7"}) == {"pixel_size": 32, "face": 7}
    for name in ("show_co2", "show_power", "show_thermostat"):
        with pytest.raises(vol.Invalid):
            service_schema(name)({})


@pytest.mark.parametrize("duration", [float("nan"), float("inf"), -1])
def test_invalid_message_duration(duration):
    with pytest.raises(vol.Invalid):
        service_schema("show_message")({"message": "Hello", "duration": duration})


@pytest.mark.parametrize("size", [32, 64])
@pytest.mark.parametrize("condition", ["sunny", "lightning-rainy", "snowy", "unknown"])
def test_weather_gif_decodes_all_frames(size, condition):
    data = render_weather_gif(WeatherData(condition, 23, humidity=60), size)
    with Image.open(io.BytesIO(data)) as image:
        assert image.size == (size, size)
        assert image.n_frames > 1
        assert image.info["loop"] == 0
        for frame in range(image.n_frames):
            image.seek(frame)
            image.load()


@pytest.mark.parametrize("style", ["card", "alert", "party", "marquee", "typewriter"])
def test_message_styles_are_valid_and_render(style):
    service_schema("show_message")({"message": "Hello", "style": style})
    data = render_message_gif(MessageSpec(text="Hello", style=style), 64)
    with Image.open(io.BytesIO(data)) as image:
        for frame in range(image.n_frames):
            image.seek(frame)
            image.load()


@pytest.mark.parametrize("size", [32, 64])
def test_all_dashboard_renderers(size):
    from custom_components.idotmatrix.bitcoin import TickerData, render_bitcoin_gif
    from custom_components.idotmatrix.co2 import CO2Data, render_co2_gif
    from custom_components.idotmatrix.power import PowerData, render_power_gif
    from custom_components.idotmatrix.thermostat import ThermostatData, ZoneState, render_thermostat_gif
    from custom_components.idotmatrix.sun import SunData, render_sun_gif
    from custom_components.idotmatrix.moon import MoonData, render_moon_gif
    from custom_components.idotmatrix.clockface import ClockFaceData, render_clockface_gif, render_analog_gif
    clock = ClockFaceData(12, 30, 5, 9, 12)
    cases = [
        (render_bitcoin_gif, TickerData(60000)),
        (render_co2_gif, CO2Data(2000)),
        (render_power_gif, PowerData(1200)),
        (render_thermostat_gif, ThermostatData(heat=ZoneState("heat", 20, 22, "heating"))),
        (render_sun_gif, SunData(True, .5, "6:00", "18:00", "SET 6H", "DAY 12H")),
        (render_moon_gif, MoonData(14)),
        (render_clockface_gif, clock),
        (render_analog_gif, clock),
    ]
    for render, data in cases:
        with Image.open(io.BytesIO(render(data, size))) as image:
            assert image.size == (size, size)
            for index in range(image.n_frames):
                image.seek(index)
                image.load()


def test_release_metadata_matches():
    import os
    root = Path(__file__).resolve().parents[1]
    version = json.loads((root / "custom_components/idotmatrix/manifest.json").read_text())["version"]
    assert f"## [{version}] - " in (root / "CHANGELOG.md").read_text()
    assert f"v{version} " in (root / "custom_components/idotmatrix/www/idotmatrix-card.js").read_text()
    if os.environ.get("GITHUB_REF_TYPE") == "tag":
        assert os.environ["GITHUB_REF_NAME"] == f"v{version}"
