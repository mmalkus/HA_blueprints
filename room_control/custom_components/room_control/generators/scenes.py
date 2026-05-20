"""Scene generator for room_control."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

from ..const import MANAGED_TAG, scene_id
from ..models import RoomProfile, SceneConfig

_LOGGER = logging.getLogger(__name__)

_KELVIN_TO_MIREDS = lambda k: round(1_000_000 / k)


def _build_scene_payload(area_id: str, scene: SceneConfig) -> dict:
    entities: dict[str, dict] = {}

    for light in scene.lights:
        state: dict = {"state": "on"}
        if light.brightness is not None:
            state["brightness"] = light.brightness
        if light.color_temp is not None:
            state["color_temp"] = _KELVIN_TO_MIREDS(light.color_temp)
        entities[light.entity_id] = state

    for mp in scene.media_players:
        entities[mp] = {"state": "playing"}

    for cover in scene.covers:
        entities[cover] = {"state": "open"}

    return {
        "scene_id": scene_id(area_id, scene.button, scene.clicks),
        "name": scene.name,
        "description": MANAGED_TAG,
        "entities": entities,
    }


async def sync_scenes(hass: HomeAssistant, room: RoomProfile) -> None:
    """Create or update all scenes for a room via scene.create."""
    for scene in room.scenes:
        payload = _build_scene_payload(room.area_id, scene)
        await hass.services.async_call("scene", "create", payload)
        _LOGGER.debug("room_control: created scene %s", payload["scene_id"])


async def sync_all_scenes(hass: HomeAssistant, profiles: dict[str, RoomProfile]) -> None:
    for room in profiles.values():
        await sync_scenes(hass, room)
