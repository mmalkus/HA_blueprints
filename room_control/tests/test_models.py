"""Tests for models and config schema."""
from __future__ import annotations

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import voluptuous as vol
from custom_components.room_control.schema import parse_config


MINIMAL_CONFIG = {
    "rooms": {
        "kitchen": {
            "area_id": "kitchen",
            "scenes": [],
            "switches": [],
        }
    }
}

FULL_CONFIG = {
    "rooms": {
        "living_room": {
            "area_id": "living_room",
            "left": {"type": "light", "entity_id": "light.living_room_ceiling"},
            "right": {"type": "media_player", "media_player_entity": "media_player.living_room_tv"},
            "scenes": [
                {
                    "name": "Evening",
                    "button": 1,
                    "clicks": 2,
                    "lights": [
                        {"entity": "light.living_room_ceiling", "brightness": 80, "color_temp": 2700}
                    ],
                },
                {
                    "name": "Movie",
                    "button": 1,
                    "clicks": 3,
                    "lights": [{"entity": "light.living_room_floor", "brightness": 20}],
                    "script_sequence": [{"action": "cover.close_cover"}],
                },
            ],
            "switches": [
                {"type": "ptm215z", "controller_name": "Living Room Switch"}
            ],
            "default_single_click": True,
            "hold_delay": 500,
            "dim_speed": 50,
            "volume_speed": 0.05,
        }
    }
}


def test_minimal_config_parses():
    profiles = parse_config(MINIMAL_CONFIG)
    assert "kitchen" in profiles
    assert profiles["kitchen"].area_id == "kitchen"


def test_full_config_parses():
    profiles = parse_config(FULL_CONFIG)
    room = profiles["living_room"]
    assert room.area_id == "living_room"
    assert room.left.type == "light"
    assert room.left.entity_id == "light.living_room_ceiling"
    assert room.right.type == "media_player"
    assert room.right.media_player_entity == "media_player.living_room_tv"
    assert len(room.scenes) == 2
    assert room.scenes[0].name == "Evening"
    assert room.scenes[0].button == 1
    assert room.scenes[0].clicks == 2
    assert room.scenes[0].lights[0].brightness == 80
    assert room.scenes[0].lights[0].color_temp == 2700
    assert room.scenes[1].script_sequence is not None
    assert len(room.switches) == 1
    assert room.switches[0].controller_name == "Living Room Switch"


def test_defaults_applied():
    profiles = parse_config(MINIMAL_CONFIG)
    room = profiles["kitchen"]
    assert room.z2m_base_topic == "zigbee2mqtt"
    assert room.default_single_click is True
    assert room.hold_delay == 500
    assert room.dim_speed == 50
    assert room.volume_speed == 0.05


def test_invalid_button_raises():
    config = {
        "rooms": {
            "x": {
                "area_id": "x",
                "scenes": [{"name": "Test", "button": 5, "clicks": 2}],
            }
        }
    }
    with pytest.raises(vol.Invalid):
        parse_config(config)


def test_invalid_clicks_raises():
    config = {
        "rooms": {
            "x": {
                "area_id": "x",
                "scenes": [{"name": "Test", "button": 1, "clicks": 7}],
            }
        }
    }
    with pytest.raises(vol.Invalid):
        parse_config(config)


def test_target_z2m_name_override():
    config = {
        "rooms": {
            "x": {
                "area_id": "x",
                "left": {
                    "type": "light",
                    "entity_id": "light.x_ceiling",
                    "target_z2m_name": "X Ceiling",
                },
            }
        }
    }
    profiles = parse_config(config)
    assert profiles["x"].left.target_z2m_name == "X Ceiling"
