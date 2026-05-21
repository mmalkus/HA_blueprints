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

# Blueprints bundled inside this package (custom_components/room_control/blueprints/)
_BUNDLED_BLUEPRINTS_DIR = os.path.join(os.path.dirname(__file__), "blueprints")
_BLUEPRINT_SOURCES = {
    "215Z.yaml": os.path.join(_BUNDLED_BLUEPRINTS_DIR, "215Z.yaml"),
    "multiclick_room_control.yaml": os.path.join(_BUNDLED_BLUEPRINTS_DIR, "multiclick_room_control.yaml"),
}


def _ensure_blueprints(hass: HomeAssistant, force: bool = False) -> list[str]:
    """Copy bundled blueprints into HA's blueprint dir if not already present.

    With force=True, overwrites existing files (used by the install_blueprints service).
    Returns list of filenames that were written.
    """
    dest_dir = hass.config.path("blueprints", "automation", "mmalkus")
    os.makedirs(dest_dir, exist_ok=True)

    written = []
    for fname, src in _BLUEPRINT_SOURCES.items():
        src = os.path.normpath(src)
        if not os.path.exists(src):
            _LOGGER.warning("room_control: bundled blueprint not found at %s", src)
            continue
        dst = os.path.normpath(os.path.join(dest_dir, fname))
        if os.path.exists(dst) and not force:
            _LOGGER.debug("room_control: blueprint %s already installed, skipping", fname)
            continue
        shutil.copy2(src, dst)
        written.append(fname)
        _LOGGER.info("room_control: installed blueprint %s → %s", fname, dst)

    return written


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up room_control from configuration.yaml."""
    hass.data.setdefault(DOMAIN, {"z2m_devices": {}})

    domain_config = config.get(DOMAIN, {})
    try:
        profiles = parse_config(domain_config) if domain_config else {}
    except Exception:
        _LOGGER.exception("room_control: failed to parse configuration — check your config")
        profiles = {}
    hass.data[DOMAIN]["profiles"] = profiles

    # Install blueprints if not already present
    written = _ensure_blueprints(hass)
    if written:
        try:
            await hass.services.async_call("blueprint", "reload")
        except Exception:
            _LOGGER.debug("room_control: blueprint reload skipped (HA not fully started yet)")

    # Warm the Z2M device cache for all distinct base topics
    base_topics = {r.z2m_base_topic for r in profiles.values()}
    for topic in base_topics:
        try:
            await cache_z2m_devices(hass, topic)
        except Exception:
            _LOGGER.warning("room_control: could not subscribe to Z2M bridge topic %s", topic)

    # Resolve missing Z2M names at startup (YAML path without target_z2m_name)
    for room in profiles.values():
        for pair in (room.left, room.right):
            if pair and pair.type == "light" and not pair.target_z2m_name and pair.entity_id:
                from .resolvers import resolve_z2m_friendly_name
                try:
                    name = await resolve_z2m_friendly_name(hass, pair.entity_id, room.z2m_base_topic)
                except Exception:
                    name = None
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
            try:
                await sync_all_scenes(hass, {room.area_id: room})
                await sync_scripts(hass, room)
                await sync_automations(hass, room)
            except Exception:
                _LOGGER.exception("room_control: sync failed for room %s", room.area_id)
        _LOGGER.info("room_control: sync complete (%d room(s))", len(targets))

    hass.services.async_register(DOMAIN, "sync", handle_sync)

    async def handle_install_blueprints(call: ServiceCall) -> None:
        written = _ensure_blueprints(hass, force=True)
        if written:
            try:
                await hass.services.async_call("blueprint", "reload")
            except Exception:
                _LOGGER.warning("room_control: blueprint reload failed after install")

    hass.services.async_register(DOMAIN, "install_blueprints", handle_install_blueprints)

    # Sync all rooms on startup (non-blocking — failures logged, not raised)
    async def _startup_sync() -> None:
        try:
            await hass.services.async_call(DOMAIN, "sync", {})
        except Exception:
            _LOGGER.exception("room_control: startup sync failed")

    hass.async_create_task(_startup_sync())

    return True


async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    """Set up a room from a config entry (UI-created room)."""
    hass.data.setdefault(DOMAIN, {"z2m_devices": {}, "profiles": {}})
    room_data = dict(entry.data)

    try:
        profiles = parse_config({"rooms": {room_data.get("area_id", entry.entry_id): room_data}})
    except Exception:
        _LOGGER.exception("room_control: failed to parse config entry %s", entry.entry_id)
        return False

    hass.data[DOMAIN]["profiles"].update(profiles)

    for room in profiles.values():
        try:
            await sync_all_scenes(hass, {room.area_id: room})
            await sync_scripts(hass, room)
            await sync_automations(hass, room)
        except Exception:
            _LOGGER.exception("room_control: sync failed for entry room %s", room.area_id)

    return True


async def async_unload_entry(hass: HomeAssistant, entry) -> bool:
    """Unload a config entry (room stays in HA, just stops being managed)."""
    area_id = entry.data.get("area_id", entry.entry_id)
    hass.data[DOMAIN].get("profiles", {}).pop(area_id, None)
    return True
