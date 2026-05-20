"""Tests for automation generator."""
from __future__ import annotations

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock

from custom_components.room_control.const import MANAGED_TAG
from custom_components.room_control.generators.automations import (
    build_multiclick_automation,
    build_ptm215z_automation,
    sync_automations,
)
from custom_components.room_control.models import PairConfig, RoomProfile, SceneConfig, SwitchConfig


def _living_room() -> RoomProfile:
    return RoomProfile(
        area_id="living_room",
        left=PairConfig(type="light", entity_id="light.ceiling", target_z2m_name="Living Room Ceiling"),
        right=PairConfig(type="media_player", media_player_entity="media_player.tv"),
        scenes=[
            SceneConfig(name="Evening", button=1, clicks=2),
            SceneConfig(name="Movie", button=1, clicks=3),
        ],
        switches=[SwitchConfig(type="ptm215z", controller_name="Living Room Switch")],
    )


def test_build_ptm215z_automation_structure():
    room = _living_room()
    switch = room.switches[0]
    auto = build_ptm215z_automation(room, switch)

    assert auto["id"] == "living_room_ptm215z_living_room_swit"
    assert auto["description"] == MANAGED_TAG
    assert auto["use_blueprint"]["path"] == "mmalkus/215Z.yaml"

    inp = auto["use_blueprint"]["input"]
    assert inp["scene_prefix"] == "living_room"
    assert inp["left_type"] == "light"
    assert inp["left_target_light"] == "Living Room Ceiling"
    assert inp["right_type"] == "media_player"
    assert inp["right_target_media"] == "media_player.tv"
    assert inp["default_single_click"] is True
    assert inp["hold_delay"] == 500
    assert inp["dim_speed"] == 50
    assert inp["volume_speed"] == 0.05


def test_build_ptm215z_automation_defaults_when_no_pairs():
    room = RoomProfile(area_id="bare", switches=[SwitchConfig(type="ptm215z", controller_name="sw")])
    auto = build_ptm215z_automation(room, room.switches[0])
    inp = auto["use_blueprint"]["input"]
    assert inp["left_target_light"] == ""
    assert inp["right_target_light"] == ""


def test_build_multiclick_automation_structure():
    room = RoomProfile(
        area_id="kitchen",
        scenes=[
            SceneConfig(name="Bright", button=1, clicks=2),
            SceneConfig(name="Dim", button=1, clicks=3),
        ],
        switches=[SwitchConfig(type="z2m_multiclick", mqtt_topic="zigbee2mqtt/kitchen_switch")],
    )
    auto = build_multiclick_automation(room, room.switches[0])

    assert auto["id"] == "kitchen_multiclick_zigbee2mqtt_kitchen_switch"
    assert auto["description"] == MANAGED_TAG
    assert auto["use_blueprint"]["path"] == "mmalkus/multiclick_room_control.yaml"

    inp = auto["use_blueprint"]["input"]
    assert inp["scene_prefix"] == "kitchen"
    assert inp["max_clicks"] == 3
    assert inp["mqtt_topic"] == "zigbee2mqtt/kitchen_switch"


def test_build_multiclick_max_clicks_derived():
    room = RoomProfile(
        area_id="x",
        scenes=[
            SceneConfig(name="A", button=1, clicks=2),
            SceneConfig(name="B", button=1, clicks=5),  # max for button 1
            SceneConfig(name="C", button=3, clicks=6),  # different button, ignored
        ],
        switches=[SwitchConfig(type="z2m_multiclick", mqtt_topic="t")],
    )
    auto = build_multiclick_automation(room, room.switches[0])
    assert auto["use_blueprint"]["input"]["max_clicks"] == 5


async def test_sync_automations_writes_and_reloads():
    with tempfile.TemporaryDirectory() as tmpdir:
        hass = MagicMock()
        hass.config.path = lambda f: os.path.join(tmpdir, f)
        hass.services = MagicMock()
        hass.services.async_call = AsyncMock()

        await sync_automations(hass, _living_room())

        path = os.path.join(tmpdir, "automations.yaml")
        assert os.path.exists(path)
        hass.services.async_call.assert_called_once_with("automation", "reload")


async def test_sync_automations_replaces_existing():
    with tempfile.TemporaryDirectory() as tmpdir:
        from ruamel.yaml import YAML
        yaml = YAML()
        path = os.path.join(tmpdir, "automations.yaml")
        with open(path, "w") as fh:
            yaml.dump([{
                "id": "living_room_ptm215z_living_room_swit",
                "alias": "old",
                "description": MANAGED_TAG,
            }], fh)

        hass = MagicMock()
        hass.config.path = lambda f: os.path.join(tmpdir, f)
        hass.services = MagicMock()
        hass.services.async_call = AsyncMock()

        await sync_automations(hass, _living_room())

        with open(path, encoding="utf-8") as fh:
            data = yaml.load(fh)

        matching = [a for a in data if a["id"] == "living_room_ptm215z_living_room_swit"]
        assert len(matching) == 1
        assert matching[0]["alias"] != "old"


async def test_sync_automations_skips_when_no_switches():
    hass = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()

    room = RoomProfile(area_id="empty")
    await sync_automations(hass, room)
    hass.services.async_call.assert_not_called()
