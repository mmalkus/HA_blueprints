"""Room Control integration."""
from __future__ import annotations

import logging
import os
import shutil
from typing import TYPE_CHECKING

import voluptuous as vol

from .const import DOMAIN
from .resolvers import cache_z2m_devices
from .schema import parse_config
from .generators.scenes import sync_all_scenes
from .generators.scripts import sync_scripts
from .generators.automations import sync_automations

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({}, extra=vol.ALLOW_EXTRA)}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up room_control from configuration.yaml."""
    hass.data.setdefault(DOMAIN, {"z2m_devices": {}})

    domain_config = config.get(DOMAIN, {})
    profiles = parse_config(domain_config) if domain_config else {}
    hass.data[DOMAIN]["profiles"] = profiles

    # Warm the Z2M device cache for all distinct base topics
    base_topics = {r.z2m_base_topic for r in profiles.values()}
    for topic in base_topics:
        await cache_z2m_devices(hass, topic)

    # Resolve missing Z2M names at startup (YAML path without target_z2m_name)
    for room in profiles.values():
        for pair in (room.left, room.right):
            if pair and pair.type == "light" and not pair.target_z2m_name and pair.entity_id:
                from .resolvers import resolve_z2m_friendly_name
                name = await resolve_z2m_friendly_name(hass, pair.entity_id, room.z2m_base_topic)
                if name:
                    pair.target_z2m_name = name
                else:
                    _LOGGER.warning(
                        "room_control: could not resolve Z2M name for %s in room %s — "
                        "automation will be skipped. Set target_z2m_name manually as a fallback.",
                        pair.entity_id,
                        room.area_id,
                    )

    async def handle_sync(call: ServiceCall) -> None:
        area_id = call.data.get("area_id")
        targets = (
            [profiles[area_id]] if area_id and area_id in profiles
            else list(profiles.values())
        )
        for room in targets:
            await sync_all_scenes(hass, {room.area_id: room})
            await sync_scripts(hass, room)
            await sync_automations(hass, room)
        _LOGGER.info("room_control: sync complete (%d room(s))", len(targets))

    hass.services.async_register(DOMAIN, "sync", handle_sync)

    # Blueprint install service
    _bundled_blueprints_dir = os.path.join(os.path.dirname(__file__), "..", "..", "blueprints")

    async def handle_install_blueprints(call: ServiceCall) -> None:
        dest_dir = hass.config.path("blueprints", "automation", "mmalkus")
        os.makedirs(dest_dir, exist_ok=True)

        installed = []
        for fname in ("215Z.yaml", "multiclick_room_control.yaml"):
            src = os.path.join(_bundled_blueprints_dir, fname)
            if not os.path.exists(src):
                # 215Z.yaml lives one level up alongside this integration
                src = os.path.join(os.path.dirname(__file__), "..", "..", "..", "215Z.yaml")
            if not os.path.exists(src):
                _LOGGER.warning("room_control: bundled blueprint %s not found", fname)
                continue
            dst = os.path.join(dest_dir, fname)
            if os.path.exists(dst):
                _LOGGER.info("room_control: blueprint %s already installed", fname)
            shutil.copy2(src, dst)
            installed.append(fname)
            _LOGGER.info("room_control: installed blueprint %s → %s", fname, dst)

        if installed:
            await hass.services.async_call("blueprint", "reload")

    hass.services.async_register(DOMAIN, "install_blueprints", handle_install_blueprints)

    # Sync all rooms on startup
    hass.async_create_task(
        hass.services.async_call(DOMAIN, "sync", {})
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    """Set up a room from a config entry (UI-created room)."""
    from .schema import parse_config

    hass.data.setdefault(DOMAIN, {"z2m_devices": {}, "profiles": {}})
    room_data = dict(entry.data)

    # Wrap single room into the parse_config format
    profiles = parse_config({"rooms": {room_data.get("area_id", entry.entry_id): room_data}})
    hass.data[DOMAIN]["profiles"].update(profiles)

    for room in profiles.values():
        await sync_all_scenes(hass, {room.area_id: room})
        await sync_scripts(hass, room)
        await sync_automations(hass, room)

    return True


async def async_unload_entry(hass: HomeAssistant, entry) -> bool:
    """Unload a config entry (room stays in HA, just stops being managed)."""
    area_id = entry.data.get("area_id", entry.entry_id)
    hass.data[DOMAIN].get("profiles", {}).pop(area_id, None)
    return True
