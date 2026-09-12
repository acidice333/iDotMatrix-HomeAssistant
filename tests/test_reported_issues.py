"""Regression coverage for historical GitHub issue reports."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import AbortFlow

from custom_components.idotmatrix import _async_register_lovelace_resource
from custom_components.idotmatrix.config_flow import ConfigFlow, OptionsFlowHandler, normalize_address
from custom_components.idotmatrix.const import CONF_MAC, DOMAIN


@pytest.mark.asyncio
@pytest.mark.parametrize("modern", [True, False])
async def test_lovelace_registration_current_and_legacy_data(tmp_path, modern):
    hass = HomeAssistant(str(tmp_path))
    resources = SimpleNamespace(loaded=False, async_load=AsyncMock(), async_items=Mock(return_value=[]), async_create_item=AsyncMock())
    hass.data[DOMAIN] = {"_static_path_registered": True}
    hass.data["lovelace"] = SimpleNamespace(resources=resources) if modern else {"resources": resources}
    await _async_register_lovelace_resource(hass)
    resources.async_create_item.assert_awaited_once_with({"res_type": "module", "url": "/idotmatrix/idotmatrix-card.js?v=1.3.0"})


@pytest.mark.asyncio
async def test_lovelace_existing_resource_gets_version_update(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    resources = SimpleNamespace(loaded=True, async_items=Mock(return_value=[{"id": "x", "url": "/idotmatrix/idotmatrix-card.js?v=1.0.0"}]), async_create_item=AsyncMock(), async_update_item=AsyncMock())
    hass.data[DOMAIN] = {"_static_path_registered": True}
    hass.data["lovelace"] = SimpleNamespace(resources=resources)
    await _async_register_lovelace_resource(hass)
    resources.async_update_item.assert_awaited_once()
    resources.async_create_item.assert_not_awaited()


@pytest.mark.parametrize("address", ["aa:bb:cc:dd:ee:ff", "AA-BB-CC-DD-EE-FF", "aabbccddeeff", " AA:BB:CC:DD:EE:FF "])
def test_address_formats_have_one_identity(address):
    assert normalize_address(address) == "AA:BB:CC:DD:EE:FF"


@pytest.mark.asyncio
async def test_repeated_discovery_cannot_create_duplicate_entries():
    flow = ConfigFlow()
    flow.async_set_unique_id = AsyncMock()
    flow._async_current_entries = Mock(return_value=[SimpleNamespace(data={CONF_MAC: "aa-bb-cc-dd-ee-ff"})])
    for _ in range(2001):
        with pytest.raises(AbortFlow, match="already_configured"):
            await flow._async_claim_address("AA:BB:CC:DD:EE:FF")


def test_options_flow_constructs_on_current_home_assistant():
    assert isinstance(ConfigFlow.async_get_options_flow(None), OptionsFlowHandler)
