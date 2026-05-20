"""Automation generator for room_control."""
from __future__ import annotations

import io
import logging
import os
from typing import TYPE_CHECKING

from ruamel.yaml import YAML

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

from ..const import MANAGED_TAG, multiclick_automation_id, ptm215z_automation_id
from ..models import RoomProfile, SwitchConfig

_LOGGER = logging.getLogger(__name__)

_yaml = YAML()
_yaml.default_flow_style = False
_yaml.preserve_quotes = True

BLUEPRINT_PATH = "mmalkus/215Z.yaml"
MULTICLICK_BLUEPRINT_PATH = "mmalkus/multiclick_room_control.yaml"


def build_ptm215z_automation(room: RoomProfile, switch: SwitchConfig) -> dict:
    left = room.left
    right = room.right
    return {
        "id": ptm215z_automation_id(room.area_id, switch),
        "alias": f"{room.area_id} — ptm215z {switch.controller_name or ''}".strip(),
        "description": MANAGED_TAG,
        "use_blueprint": {
            "path": BLUEPRINT_PATH,
            "input": {
                "base_topic": room.z2m_base_topic,
                "controller": switch.controller_name or "",
                "controller_event": switch.controller_event or "",
                "scene_prefix": room.area_id,
                "left_type": left.type if left else "light",
                "left_target_light": (left.target_z2m_name or "") if left and left.type == "light" else "",
                "left_target_media": (left.media_player_entity or "") if left and left.type == "media_player" else "",
                "right_type": right.type if right else "light",
                "right_target_light": (right.target_z2m_name or "") if right and right.type == "light" else "",
                "right_target_media": (right.media_player_entity or "") if right and right.type == "media_player" else "",
                "default_single_click": room.default_single_click,
                "hold_delay": room.hold_delay,
                "dim_speed": room.dim_speed,
                "volume_speed": room.volume_speed,
            },
        },
    }


def build_multiclick_automation(room: RoomProfile, switch: SwitchConfig) -> dict:
    max_clicks = max(
        (s.clicks for s in room.scenes if s.button == 1),
        default=4,
    )
    return {
        "id": multiclick_automation_id(room.area_id, switch),
        "alias": f"{room.area_id} — multiclick {switch.mqtt_topic or ''}".strip(),
        "description": MANAGED_TAG,
        "use_blueprint": {
            "path": MULTICLICK_BLUEPRINT_PATH,
            "input": {
                "scene_prefix": room.area_id,
                "button": 1,
                "trigger_type": "z2m",
                "mqtt_topic": switch.mqtt_topic or "",
                "click_action_payload": switch.click_action_payload,
                "max_clicks": max_clicks,
                "click_timeout": room.hold_delay,
            },
        },
    }


def _automations_path(hass: HomeAssistant) -> str:
    return hass.config.path("automations.yaml")


def _load_automations(path: str) -> list:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as fh:
        data = _yaml.load(fh)
    return data if isinstance(data, list) else []


def _save_automations(path: str, automations: list) -> None:
    buf = io.StringIO()
    _yaml.dump(automations, buf)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(buf.getvalue())


async def sync_automations(hass: HomeAssistant, room: RoomProfile) -> None:
    """Write managed automations for a room to automations.yaml, then reload."""
    new_entries: list[dict] = []
    for switch in room.switches:
        if switch.type == "ptm215z":
            new_entries.append(build_ptm215z_automation(room, switch))
        elif switch.type == "z2m_multiclick":
            new_entries.append(build_multiclick_automation(room, switch))
        else:
            _LOGGER.warning("room_control: switch type %s not yet supported", switch.type)

    if not new_entries:
        return

    path = _automations_path(hass)
    existing = _load_automations(path)

    new_ids = {e["id"] for e in new_entries}
    kept = [a for a in existing if a.get("id") not in new_ids]
    kept.extend(new_entries)

    _save_automations(path, kept)
    await hass.services.async_call("automation", "reload")
    _LOGGER.debug(
        "room_control: wrote %d automations for room %s", len(new_entries), room.area_id
    )
