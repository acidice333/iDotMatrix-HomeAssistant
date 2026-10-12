"""Exercise BLE discovery and retry behavior without contacting a device."""
import asyncio
import logging
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
import homeassistant  # Initialize Home Assistant before BLE validation dependencies.
import bleak_retry_connector
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.service import BleakGATTService, BleakGATTServiceCollection
from bleak.exc import BleakError

from custom_components.idotmatrix.client.connectionManager import ConnectionManager
from custom_components.idotmatrix.client.const import UUID_READ_DATA, UUID_WRITE_DATA


def fake_client(*, has_write=True, write_size=509):
    """Use a real Bleak service collection so missing UUIDs return None."""
    services = BleakGATTServiceCollection()
    service = BleakGATTService(None, 1, "0000fa00-0000-1000-8000-00805f9b34fb")
    services.add_service(service)
    for handle, uuid in enumerate((UUID_READ_DATA, UUID_WRITE_DATA) if has_write else (UUID_READ_DATA,), 2):
        services.add_characteristic(BleakGATTCharacteristic(
            None, handle, uuid, ["write", "write-without-response"], lambda: write_size, service,
        ))
    client = SimpleNamespace(
        is_connected=True, services=services, clear_cache=AsyncMock(return_value=True),
        write_gatt_char=AsyncMock(),
    )
    client.disconnect = AsyncMock(side_effect=lambda: setattr(client, "is_connected", False))
    return client


@pytest.fixture
def manager(monkeypatch):
    # Avoid the library singleton so tests cannot affect another coordinator.
    manager = object.__new__(ConnectionManager)
    ConnectionManager.__init__(manager)
    manager.address = "AA:BB:CC:DD:EE:FF"
    manager.hass = Mock()
    device = SimpleNamespace(address=manager.address, name="IDM-Test")
    monkeypatch.setitem(sys.modules, "homeassistant.components.bluetooth", SimpleNamespace(
        async_ble_device_from_address=Mock(return_value=device),
    ))
    monkeypatch.setattr(bleak_retry_connector, "establish_connection", AsyncMock())
    return manager


@pytest.mark.asyncio
async def test_missing_write_characteristic_clears_cache_and_retries_send(manager):
    stale, fresh = fake_client(has_write=False), fake_client()
    manager.client = stale
    bleak_retry_connector.establish_connection.return_value = fresh
    assert await manager.send(b"command") is True
    stale.write_gatt_char.assert_not_awaited()
    stale.clear_cache.assert_awaited_once()
    stale.disconnect.assert_awaited_once()
    assert bleak_retry_connector.establish_connection.call_args.kwargs["use_services_cache"] is False
    fresh.write_gatt_char.assert_awaited_once()


@pytest.mark.asyncio
async def test_connect_validates_services_and_recovers_stale_cache(manager):
    stale, fresh = fake_client(has_write=False), fake_client()
    bleak_retry_connector.establish_connection.side_effect = [stale, fresh]
    await manager.connect()
    assert manager.client is fresh
    stale.clear_cache.assert_awaited_once()
    stale.disconnect.assert_awaited_once()
    calls = bleak_retry_connector.establish_connection.call_args_list
    assert [call.kwargs["use_services_cache"] for call in calls] == [True, False]
    assert all(call.args[0] is bleak_retry_connector.BleakClientWithServiceCache for call in calls)
    assert all(call.kwargs["disconnected_callback"] == manager._on_disconnected for call in calls)
    stale.write_gatt_char.assert_not_awaited()
    fresh.write_gatt_char.assert_not_awaited()


@pytest.mark.asyncio
async def test_connected_client_is_validated_before_reuse(manager):
    stale, fresh = fake_client(has_write=False), fake_client()
    manager.client = stale
    bleak_retry_connector.establish_connection.return_value = fresh
    await manager.connect()
    assert manager.client is fresh
    stale.clear_cache.assert_awaited_once()


@pytest.mark.asyncio
async def test_valid_connected_client_is_reused_without_discovery(manager):
    manager.client = fake_client()
    await manager.connect()
    bleak_retry_connector.establish_connection.assert_not_awaited()
    manager.client.clear_cache.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("cache_result", [False, BleakError("cache clear unsupported")])
async def test_cache_clear_failure_still_disconnects_and_rediscovers(manager, cache_result):
    stale, fresh = fake_client(has_write=False), fake_client()
    manager.client = stale
    if isinstance(cache_result, Exception):
        stale.clear_cache.side_effect = cache_result
    else:
        stale.clear_cache.return_value = cache_result
    bleak_retry_connector.establish_connection.return_value = fresh
    await manager.connect()
    assert manager.client is fresh
    stale.disconnect.assert_awaited_once()
    assert bleak_retry_connector.establish_connection.call_args.kwargs["use_services_cache"] is False


@pytest.mark.asyncio
async def test_cancelled_cache_clear_releases_failed_connection(manager):
    stale = fake_client(has_write=False)
    stale.clear_cache.side_effect = asyncio.CancelledError()
    manager.client = stale
    with pytest.raises(asyncio.CancelledError):
        await manager.connect()
    stale.disconnect.assert_awaited_once()
    assert manager.client is None
    bleak_retry_connector.establish_connection.assert_not_awaited()


@pytest.mark.asyncio
async def test_unresolved_services_trigger_fresh_discovery(manager):
    class UnresolvedClient:
        is_connected = True
        clear_cache = AsyncMock(return_value=True)
        disconnect = AsyncMock()

        @property
        def services(self):
            raise BleakError("Service Discovery has not been performed yet")

    manager.client = UnresolvedClient()
    fresh = fake_client()
    bleak_retry_connector.establish_connection.return_value = fresh
    await manager.connect()
    assert manager.client is fresh
    UnresolvedClient.clear_cache.assert_awaited_once()
    UnresolvedClient.disconnect.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["connect", "send"])
async def test_persistently_missing_characteristic_is_diagnostic_and_bounded(manager, operation):
    stale, incompatible = fake_client(has_write=False), fake_client(has_write=False)
    if operation == "connect":
        bleak_retry_connector.establish_connection.side_effect = [stale, incompatible]
    else:
        manager.client = stale
        bleak_retry_connector.establish_connection.return_value = incompatible
    with pytest.raises(BleakError, match=UUID_WRITE_DATA) as error:
        if operation == "connect":
            await manager.connect()
        else:
            await manager.send(b"command")
    assert UUID_READ_DATA in str(error.value)
    assert "firmware" in str(error.value)
    assert bleak_retry_connector.establish_connection.await_count == (2 if operation == "connect" else 1)
    assert manager.client is None
    incompatible.disconnect.assert_awaited_once()
    stale.write_gatt_char.assert_not_awaited()
    incompatible.write_gatt_char.assert_not_awaited()


@pytest.mark.asyncio
async def test_partial_transfer_is_never_replayed(manager, monkeypatch):
    manager.client = fake_client(write_size=3)
    manager.client.write_gatt_char.side_effect = [None, BleakError("write failed")]
    reconnect = AsyncMock()
    monkeypatch.setattr(manager, "_force_reconnect", reconnect)
    with pytest.raises(BleakError, match="write failed"):
        await manager.send(b"abcdefghi")
    assert manager.client.write_gatt_char.await_count == 2
    reconnect.assert_not_awaited()


@pytest.mark.asyncio
async def test_first_write_failure_reconnects_once_without_reusing_cache(manager):
    stale, fresh = fake_client(), fake_client()
    stale.write_gatt_char.side_effect = BleakError("link lost")
    manager.client = stale
    bleak_retry_connector.establish_connection.return_value = fresh
    assert await manager.send(b"command") is True
    stale.clear_cache.assert_not_awaited()
    stale.disconnect.assert_awaited_once()
    fresh.write_gatt_char.assert_awaited_once()
    assert bleak_retry_connector.establish_connection.await_count == 1
    assert bleak_retry_connector.establish_connection.call_args.kwargs["use_services_cache"] is False


@pytest.mark.asyncio
async def test_connection_failure_propagates_without_claiming_success(manager):
    bleak_retry_connector.establish_connection.side_effect = BleakError("out of connection slots")
    with pytest.raises(BleakError, match="out of connection slots"):
        await manager.connect()
    assert manager.client is None


@pytest.mark.asyncio
async def test_cancelled_write_does_not_reconnect(manager, monkeypatch):
    manager.client = fake_client()
    manager.client.write_gatt_char.side_effect = asyncio.CancelledError()
    reconnect = AsyncMock()
    monkeypatch.setattr(manager, "_force_reconnect", reconnect)
    with pytest.raises(asyncio.CancelledError):
        await manager.send(b"command")
    reconnect.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("response,reported_size", [(True, 1024), (False, 20)])
async def test_valid_transfer_keeps_chunk_limits_and_write_mode(manager, response, reported_size):
    manager.client = fake_client(write_size=reported_size)
    payload = bytes(range(256)) * 4
    assert await manager.send(payload, response=response)
    calls = manager.client.write_gatt_char.call_args_list
    assert b"".join(call.args[1] for call in calls) == payload
    assert all(len(call.args[1]) <= min(reported_size, 509) for call in calls)
    assert all(call.kwargs["response"] is response for call in calls)


@pytest.mark.asyncio
async def test_debug_logs_capture_recovery_and_progress_without_payloads(manager, caplog):
    caplog.set_level(logging.DEBUG, logger=manager.logging.name)
    device = SimpleNamespace(address=manager.address, name="IDM-Test", details={
        "source": "proxy-test", "path": "/org/bluez/hci0/dev_test",
        "manufacturer_data": "private-advertisement-content",
    })
    bluetooth = sys.modules["homeassistant.components.bluetooth"]
    bluetooth.async_ble_device_from_address.return_value = device
    bluetooth.async_last_service_info = Mock(return_value=SimpleNamespace(source="proxy-test", rssi=-64))
    stale, fresh = fake_client(has_write=False), fake_client(write_size=3)
    fresh.backend_id, fresh.mtu_size = "esphome", 512
    bleak_retry_connector.establish_connection.side_effect = [stale, fresh]
    await manager.connect()
    await manager.send(b"private-display-content")
    logs = caplog.text
    assert "homeassistant=" in logs and "bleak-retry-connector=" in logs
    assert "attempt=1/2 service_cache=True" in logs
    assert "attempt=2/2 service_cache=False" in logs
    assert "selected_source=proxy-test" in logs and "rssi=-64" in logs
    assert "backend=esphome mtu=512" in logs
    assert UUID_WRITE_DATA in logs and "properties=" in logs
    assert "BLE cache clear" in logs and "success=True" in logs
    assert "BLE write complete" in logs and "chunk_size=3" in logs
    assert "private-display-content" not in logs
    assert "private-advertisement-content" not in logs


@pytest.mark.asyncio
async def test_debug_write_failure_records_exact_progress_and_traceback(manager, caplog):
    caplog.set_level(logging.DEBUG, logger=manager.logging.name)
    manager.client = fake_client(write_size=3)
    manager.client.write_gatt_char.side_effect = [None, BleakError("radio failure")]
    with pytest.raises(BleakError, match="radio failure"):
        await manager.send(b"abcdefghi")
    assert "chunk=2/3 offset=3 size=3 completed_chunks=1" in caplog.text
    assert "partial transfer" in caplog.text
    assert any(record.exc_info for record in caplog.records if "BLE chunk failed" in record.message)
    assert "abcdefghi" not in caplog.text


@pytest.mark.asyncio
async def test_optional_debug_metadata_failure_does_not_break_connection(manager, caplog):
    class ClientWithUnavailableMetadata(SimpleNamespace):
        @property
        def backend_id(self):
            raise BleakError("backend unavailable")

        @property
        def mtu_size(self):
            raise BleakError("MTU unavailable")

    caplog.set_level(logging.DEBUG, logger=manager.logging.name)
    client = ClientWithUnavailableMetadata(**vars(fake_client()))
    bleak_retry_connector.establish_connection.return_value = client
    bluetooth = sys.modules["homeassistant.components.bluetooth"]
    bluetooth.async_last_service_info = Mock(side_effect=RuntimeError("routing info unavailable"))
    await manager.connect()
    assert await manager.send(b"command") is True
    assert "backend=unavailable mtu=unavailable" in caplog.text
    assert "routing details unavailable" in caplog.text


@pytest.mark.asyncio
async def test_optional_diagnostics_are_not_read_with_debug_disabled(manager, caplog):
    caplog.set_level(logging.INFO, logger=manager.logging.name)
    bluetooth = sys.modules["homeassistant.components.bluetooth"]
    bluetooth.async_last_service_info = Mock(side_effect=AssertionError("debug lookup should be skipped"))
    bleak_retry_connector.establish_connection.return_value = fake_client()
    await manager.connect()
    bluetooth.async_last_service_info.assert_not_called()
    assert manager._debug_versions is None
    assert not any(record.levelno == logging.DEBUG for record in caplog.records)


def test_disconnect_callback_logs_link_state(manager, caplog):
    caplog.set_level(logging.DEBUG, logger=manager.logging.name)
    client = fake_client()
    client.is_connected = False
    manager._on_disconnected(client)
    assert "disconnect callback" in caplog.text
    assert "connected=False" in caplog.text
