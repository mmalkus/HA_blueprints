"""Z2M name resolution for room_control."""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def cache_z2m_devices(hass: HomeAssistant, base_topic: str) -> None:
    """Subscribe to {base_topic}/bridge/devices and cache IEEE → friendly_name.

    Z2M publishes a JSON array on this topic at startup:
    [{"ieee_address": "0x...", "friendly_name": "Living Room Ceiling", ...}]

    Stores result in hass.data[DOMAIN]["z2m_devices"] = {ieee: friendly_name}.
    Called once during async_setup before config is parsed.
    """
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("z2m_devices", {})

    topic = f"{base_topic}/bridge/devices"

    async def _handle_message(msg) -> None:
        try:
            devices = json.loads(msg.payload)
        except (json.JSONDecodeError, TypeError):
            _LOGGER.warning("room_control: could not parse Z2M bridge/devices payload")
            return
        hass.data[DOMAIN]["z2m_devices"] = {
            d["ieee_address"]: d["friendly_name"]
            for d in devices
            if "ieee_address" in d and "friendly_name" in d
        }
        _LOGGER.debug(
            "room_control: cached %d Z2M devices", len(hass.data[DOMAIN]["z2m_devices"])
        )

    await hass.components.mqtt.async_subscribe(topic, _handle_message)


async def resolve_z2m_friendly_name(
    hass: HomeAssistant,
    entity_id: str,
    base_topic: str = "zigbee2mqtt",
) -> str | None:
    """Resolve Z2M friendly name from a HA light entity_id.

    Steps:
    1. entity_id → device_id  (entity registry)
    2. device_id → IEEE       (device registry, identifier prefix "zigbee2mqtt_")
    3. IEEE → friendly_name   (hass.data[DOMAIN]["z2m_devices"] cache)

    Returns None with a warning log if any step fails.
    """
    from homeassistant.helpers import entity_registry as er, device_registry as dr

    ent_reg = er.async_get(hass)
    entry = ent_reg.async_get(entity_id)
    if not entry or not entry.device_id:
        _LOGGER.warning("room_control: entity %s not found in entity registry", entity_id)
        return None

    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get(entry.device_id)
    if not device:
        _LOGGER.warning("room_control: no device found for entity %s", entity_id)
        return None

    ieee = next(
        (
            ident.removeprefix("zigbee2mqtt_")
            for domain, ident in device.identifiers
            if domain == "mqtt" and ident.startswith("zigbee2mqtt_")
        ),
        None,
    )
    if not ieee:
        _LOGGER.warning(
            "room_control: %s is not a Z2M device (no zigbee2mqtt_ identifier)", entity_id
        )
        return None

    z2m_devices: dict = hass.data.get(DOMAIN, {}).get("z2m_devices", {})
    name = z2m_devices.get(ieee)
    if not name:
        _LOGGER.warning(
            "room_control: IEEE %s not found in Z2M device cache (is Zigbee2MQTT running?)",
            ieee,
        )
    return name
