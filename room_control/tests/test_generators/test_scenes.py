"""Tests for scene generator."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, call

from custom_components.room_control.generators.scenes import (
    _KELVIN_TO_MIREDS,
    _build_scene_payload,
    sync_scenes,
)
from custom_components.room_control.models import LightConfig, RoomProfile, SceneConfig


def test_kelvin_to_mireds():
    assert _KELVIN_TO_MIREDS(4000) == 250
    assert _KELVIN_TO_MIREDS(2700) == 370
    assert _KELVIN_TO_MIREDS(6500) == 154


def test_scene_payload_basic():
    scene = SceneConfig(
        name="Evening",
        button=1,
        clicks=2,
        lights=[LightConfig(entity_id="light.ceiling", brightness=80, color_temp=2700)],
    )
    payload = _build_scene_payload("living_room", scene)

    assert payload["scene_id"] == "living_room_1_2"
    assert payload["name"] == "Evening"
    assert payload["description"] == "room_control_managed"
    assert payload["entities"]["light.ceiling"]["brightness"] == 80
    assert payload["entities"]["light.ceiling"]["color_temp"] == 370  # mireds
    assert payload["entities"]["light.ceiling"]["state"] == "on"


def test_scene_payload_no_brightness_or_temp():
    scene = SceneConfig(
        name="On",
        button=2,
        clicks=2,
        lights=[LightConfig(entity_id="light.floor")],
    )
    payload = _build_scene_payload("kitchen", scene)
    assert payload["entities"]["light.floor"] == {"state": "on"}
    assert "brightness" not in payload["entities"]["light.floor"]
    assert "color_temp" not in payload["entities"]["light.floor"]


def test_scene_payload_media_player():
    scene = SceneConfig(
        name="Music",
        button=3,
        clicks=2,
        media_players=["media_player.tv"],
    )
    payload = _build_scene_payload("living_room", scene)
    assert payload["entities"]["media_player.tv"] == {"state": "playing"}


def test_scene_payload_cover():
    scene = SceneConfig(
        name="Movie",
        button=1,
        clicks=3,
        covers=["cover.blinds"],
    )
    payload = _build_scene_payload("living_room", scene)
    assert payload["entities"]["cover.blinds"] == {"state": "open"}


def test_scene_payload_all_four_buttons():
    for button in range(1, 5):
        scene = SceneConfig(name="Test", button=button, clicks=2)
        payload = _build_scene_payload("room", scene)
        assert payload["scene_id"] == f"room_{button}_2"


async def test_sync_scenes_calls_service_per_scene():
    hass = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()

    room = RoomProfile(
        area_id="living_room",
        scenes=[
            SceneConfig(name="Evening", button=1, clicks=2,
                        lights=[LightConfig(entity_id="light.ceil", brightness=80)]),
            SceneConfig(name="Movie", button=1, clicks=3,
                        lights=[LightConfig(entity_id="light.floor", brightness=20)]),
        ],
    )

    await sync_scenes(hass, room)

    assert hass.services.async_call.call_count == 2
    calls = hass.services.async_call.call_args_list
    assert calls[0][0][0] == "scene"
    assert calls[0][0][1] == "create"
    assert calls[0][0][2]["scene_id"] == "living_room_1_2"
    assert calls[1][0][2]["scene_id"] == "living_room_1_3"


async def test_sync_scenes_empty_room():
    hass = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()

    room = RoomProfile(area_id="empty_room")
    await sync_scenes(hass, room)

    hass.services.async_call.assert_not_called()
