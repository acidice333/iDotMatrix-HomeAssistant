"""Local card harness: real rendering/validation, simulated device writes."""
import asyncio
import base64
import io
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import Mock

from aiohttp import web
from homeassistant.core import HomeAssistant
from homeassistant.helpers.template import Template
import yaml

from custom_components.idotmatrix.coordinator import IDotMatrixCoordinator
from custom_components.idotmatrix.service_validation import service_schema

ROOT = Path(__file__).resolve().parents[1]

async def main():
    temporary = tempfile.TemporaryDirectory(prefix="idotmatrix-card-")
    hass = HomeAssistant(temporary.name)
    hass.states.async_set("sensor.room_temperature", "22.5")
    hass.states.async_set("sensor.living_room_co2", "650")
    entry = SimpleNamespace(options={}, entry_id="card-test", async_on_unload=Mock())
    coordinator = IDotMatrixCoordinator(hass, entry)
    designs = {}
    async def index(request):
        return web.FileResponse(ROOT / "tests/card/index.html")
    async def card(request):
        return web.FileResponse(ROOT / "custom_components/idotmatrix/www/idotmatrix-card.js")
    async def api(request):
        message = await request.json()
        typ = message.get("type")
        if typ == "render_template":
            return web.json_response({"result": str(Template(message["template"], hass).async_render(parse_result=False))})
        if typ == "idotmatrix/list_designs":
            return web.json_response({"designs": designs})
        if typ == "idotmatrix/save_design":
            designs[message["name"]] = message
            return web.json_response({})
        if typ == "idotmatrix/delete_design":
            designs.pop(message["name"], None)
            return web.json_response({})
        service, data = message.get("service"), message.get("service_data", {})
        if service == "list_fonts":
            fonts = [{"filename": p.name, "name": p.stem} for p in (ROOT / "custom_components/idotmatrix/fonts").iterdir() if p.suffix in (".ttf", ".otf", ".bdf")]
            return web.json_response({"response": {"fonts": fonts}})
        if service == "render_preview":
            image = await coordinator._render_face(data["face"]["layers"], data.get("screen_size", 32))
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            return web.json_response({"response": {"image": "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()}})
        if service and (service.startswith("show_") or service == "display_gif"):
            try:
                service_schema(service)(data)
            except Exception as error:
                return web.json_response({"error": str(error)}, status=400)
        return web.json_response({"context": {"id": "simulated-device-write"}})
    async def services(request):
        return web.json_response(yaml.safe_load((ROOT / "custom_components/idotmatrix/services.yaml").read_text()))
    app = web.Application()
    app.add_routes([web.get('/', index), web.get('/card.js', card), web.post('/api', api), web.get('/services', services)])
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '127.0.0.1', 8129).start()
    print('Card harness: http://127.0.0.1:8129 (simulated BLE)', flush=True)
    await asyncio.Event().wait()

asyncio.run(main())
