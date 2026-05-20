"""Script generator for room_control."""
from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from ruamel.yaml import YAML

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

from ..const import MANAGED_TAG, script_entity, scene_id
from ..models import RoomProfile

_LOGGER = logging.getLogger(__name__)

_yaml = YAML()
_yaml.default_flow_style = False
_yaml.preserve_quotes = True


def _scripts_path(hass: HomeAssistant) -> str:
    return hass.config.path("scripts.yaml")


def _load_scripts(path: str) -> list:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as fh:
        data = _yaml.load(fh)
    if data is None:
        return []
    if isinstance(data, list):
        return data
    # scripts.yaml can also be a dict keyed by alias; normalize to list
    return list(data.values()) if isinstance(data, dict) else []


def _save_scripts(path: str, scripts: list) -> None:
    import io
    buf = io.StringIO()
    _yaml.dump(scripts, buf)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(buf.getvalue())


def build_script_entries(room: RoomProfile) -> list[dict]:
    """Return a list of script dicts for scenes that have script_sequence set."""
    entries = []
    for scene in room.scenes:
        if scene.script_sequence is None:
            continue
        entries.append({
            "alias": f"{room.area_id} — {scene.name}",
            "id": scene_id(room.area_id, scene.button, scene.clicks),
            "description": MANAGED_TAG,
            "sequence": scene.script_sequence,
        })
    return entries


async def sync_scripts(hass: HomeAssistant, room: RoomProfile) -> None:
    """Write managed scripts for a room to scripts.yaml, then reload."""
    new_entries = build_script_entries(room)
    if not new_entries:
        return

    path = _scripts_path(hass)
    existing = _load_scripts(path)

    # Remove any existing managed entries for this room's script IDs
    new_ids = {e["id"] for e in new_entries}
    kept = [s for s in existing if s.get("id") not in new_ids]
    kept.extend(new_entries)

    _save_scripts(path, kept)
    await hass.services.async_call("script", "reload")
    _LOGGER.debug("room_control: wrote %d scripts for room %s", len(new_entries), room.area_id)
