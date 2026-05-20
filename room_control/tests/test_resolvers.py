"""Tests for Z2M name resolution."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

# conftest installs HA stubs before this runs


def _make_hass(z2m_devices: dict | None = None) -> MagicMock:
    hass = MagicMock()
    hass.data = {"room_control": {"z2m_devices": z2m_devices or {}}}
    return hass


def _make_entity_entry(device_id: str | None) -> MagicMock:
    entry = MagicMock()
    entry.device_id = device_id
    return entry


def _make_device(identifiers: set) -> MagicMock:
    device = MagicMock()
    device.identifiers = identifiers
    return device


@pytest.mark.asyncio
async def test_resolve_happy_path():
    from custom_components.room_control.resolvers import resolve_z2m_friendly_name

    hass = _make_hass({"0xabc": "Living Room Ceiling"})
    entity_entry = _make_entity_entry("dev-1")
    device = _make_device({("mqtt", "zigbee2mqtt_0xabc")})

    with (
        patch(
            "homeassistant.helpers.entity_registry.async_get",
            return_value=MagicMock(async_get=MagicMock(return_value=entity_entry)),
        ),
        patch(
            "homeassistant.helpers.device_registry.async_get",
            return_value=MagicMock(async_get=MagicMock(return_value=device)),
        ),
    ):
        result = await resolve_z2m_friendly_name(hass, "light.living_room_ceiling")

    assert result == "Living Room Ceiling"


@pytest.mark.asyncio
async def test_resolve_entity_not_in_registry():
    from custom_components.room_control.resolvers import resolve_z2m_friendly_name

    hass = _make_hass()
    with patch(
        "homeassistant.helpers.entity_registry.async_get",
        return_value=MagicMock(async_get=MagicMock(return_value=None)),
    ):
        result = await resolve_z2m_friendly_name(hass, "light.unknown")

    assert result is None


@pytest.mark.asyncio
async def test_resolve_not_z2m_device():
    from custom_components.room_control.resolvers import resolve_z2m_friendly_name

    hass = _make_hass()
    entity_entry = _make_entity_entry("dev-2")
    device = _make_device({("hue", "hue_abc123")})  # no zigbee2mqtt_ identifier

    with (
        patch(
            "homeassistant.helpers.entity_registry.async_get",
            return_value=MagicMock(async_get=MagicMock(return_value=entity_entry)),
        ),
        patch(
            "homeassistant.helpers.device_registry.async_get",
            return_value=MagicMock(async_get=MagicMock(return_value=device)),
        ),
    ):
        result = await resolve_z2m_friendly_name(hass, "light.hue_bulb")

    assert result is None


@pytest.mark.asyncio
async def test_resolve_cache_empty():
    from custom_components.room_control.resolvers import resolve_z2m_friendly_name

    hass = _make_hass(z2m_devices={})  # IEEE not in cache
    entity_entry = _make_entity_entry("dev-3")
    device = _make_device({("mqtt", "zigbee2mqtt_0xdef")})

    with (
        patch(
            "homeassistant.helpers.entity_registry.async_get",
            return_value=MagicMock(async_get=MagicMock(return_value=entity_entry)),
        ),
        patch(
            "homeassistant.helpers.device_registry.async_get",
            return_value=MagicMock(async_get=MagicMock(return_value=device)),
        ),
    ):
        result = await resolve_z2m_friendly_name(hass, "light.living_room_ceiling")

    assert result is None


@pytest.mark.asyncio
async def test_cache_z2m_devices_parses_payload():
    from custom_components.room_control.resolvers import cache_z2m_devices

    hass = MagicMock()
    hass.data = {}
    captured_callback = {}

    async def fake_subscribe(topic, callback):
        captured_callback["fn"] = callback

    hass.components.mqtt.async_subscribe = fake_subscribe

    await cache_z2m_devices(hass, "zigbee2mqtt")

    msg = MagicMock()
    msg.payload = json.dumps([
        {"ieee_address": "0xabc", "friendly_name": "Living Room Ceiling"},
        {"ieee_address": "0xdef", "friendly_name": "Kitchen"},
    ])
    await captured_callback["fn"](msg)

    assert hass.data["room_control"]["z2m_devices"]["0xabc"] == "Living Room Ceiling"
    assert hass.data["room_control"]["z2m_devices"]["0xdef"] == "Kitchen"


@pytest.mark.asyncio
async def test_cache_z2m_devices_bad_payload():
    from custom_components.room_control.resolvers import cache_z2m_devices

    hass = MagicMock()
    hass.data = {}
    captured_callback = {}

    async def fake_subscribe(topic, callback):
        captured_callback["fn"] = callback

    hass.components.mqtt.async_subscribe = fake_subscribe

    await cache_z2m_devices(hass, "zigbee2mqtt")

    msg = MagicMock()
    msg.payload = "not json"
    await captured_callback["fn"](msg)  # should not raise

    assert hass.data["room_control"]["z2m_devices"] == {}
